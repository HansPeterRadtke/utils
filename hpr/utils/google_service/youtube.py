#!/usr/bin/env python3
"""Small YouTube operator CLI using the shared Multiverse OAuth credential."""
import os
os.umask(0o077)
import argparse
import json
import mimetypes
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.parse
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import google_service as g

CHUNK = 8 * 1024 * 1024  # multiple of 256 KiB, required by resumable uploads


def auth_header():
    token, _ = g.access_token()
    return {"Authorization": "Bearer " + token}


def own_channel():
    data = g.api_json("https://www.googleapis.com/youtube/v3/channels?" + urllib.parse.urlencode({
        "part": "id,snippet,contentDetails,statistics", "mine": "true"
    }))
    items = data.get("items", [])
    if len(items) != 1:
        raise RuntimeError(f"Expected exactly one authenticated YouTube channel, found {len(items)}")
    return items[0]


def channel_cmd(_args):
    item = own_channel(); snippet = item.get("snippet", {}); stats = item.get("statistics", {})
    print("title=" + str(snippet.get("title")))
    print("handle=" + str(snippet.get("customUrl")))
    print("channel_id=" + str(item.get("id")))
    print("subscribers=" + str(stats.get("subscriberCount")))
    print("videos=" + str(stats.get("videoCount")))
    return 0


def list_cmd(args):
    channel = own_channel()
    playlist = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not playlist:
        raise RuntimeError("Authenticated channel has no uploads playlist")
    data = g.api_json("https://www.googleapis.com/youtube/v3/playlistItems?" + urllib.parse.urlencode({
        "part": "snippet,contentDetails", "playlistId": playlist, "maxResults": min(args.limit, 50)
    }))
    ids = [x.get("contentDetails", {}).get("videoId") for x in data.get("items", [])]
    ids = [x for x in ids if x]
    details = {}
    if ids:
        videos = g.api_json("https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode({
            "part": "id,snippet,status,processingDetails", "id": ",".join(ids)
        }))
        details = {x["id"]: x for x in videos.get("items", [])}
    for vid in ids:
        item = details.get(vid, {}); sn = item.get("snippet", {}); st = item.get("status", {}); proc = item.get("processingDetails", {})
        print("\t".join((vid, str(st.get("privacyStatus")), str(proc.get("processingStatus")), str(sn.get("title")))))
    return 0


def start_resumable(path, title, description, privacy, category):
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    size = path.stat().st_size
    metadata = {"snippet": {"title": title, "description": description, "categoryId": str(category)},
                "status": {"privacyStatus": privacy}}
    params = {"uploadType": "resumable", "part": "snippet,status", "notifySubscribers": "false"}
    headers = auth_header() | {"Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": mime,
                              "X-Upload-Content-Length": str(size)}
    response = requests.post("https://www.googleapis.com/upload/youtube/v3/videos", params=params,
                             headers=headers, data=json.dumps(metadata), timeout=60)
    response.raise_for_status()
    location = response.headers.get("Location")
    if not location:
        raise RuntimeError("YouTube did not return a resumable upload URL")
    return location, mime, size


def upload_file(path, title, description="", privacy="private", category="22"):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    location, mime, size = start_resumable(path, title, description, privacy, category)
    offset = 0; result = None
    with path.open("rb") as stream:
        while offset < size:
            chunk = stream.read(CHUNK)
            if not chunk:
                break
            end = offset + len(chunk) - 1
            headers = auth_header() | {"Content-Type": mime, "Content-Length": str(len(chunk)),
                                       "Content-Range": f"bytes {offset}-{end}/{size}"}
            response = requests.put(location, headers=headers, data=chunk, timeout=300)
            if response.status_code == 308:
                acknowledged = response.headers.get("Range")
                offset = end + 1
                if acknowledged and "-" in acknowledged:
                    offset = int(acknowledged.rsplit("-", 1)[1]) + 1
                    stream.seek(offset)
                continue
            response.raise_for_status()
            result = response.json(); offset = size
    if not result or not result.get("id"):
        raise RuntimeError("YouTube upload completed without returning a video ID")
    return result


def upload_cmd(args):
    result = upload_file(args.file, args.title, args.description, args.privacy, args.category)
    vid = result["id"]
    print("video_id=" + vid)
    print("privacy=" + str(result.get("status", {}).get("privacyStatus")))
    print("url=https://www.youtube.com/watch?v=" + vid)
    return 0


def delete_video(video_id):
    response = requests.delete("https://www.googleapis.com/youtube/v3/videos", params={"id": video_id},
                               headers=auth_header(), timeout=60)
    if response.status_code not in (204, 404):
        response.raise_for_status()

def wait_deleted(video_id, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        check = g.api_json("https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode({"part": "id", "id": video_id}))
        if not check.get("items"):
            return True
        time.sleep(2)
    return False


def delete_cmd(args):
    delete_video(args.video_id)
    if not wait_deleted(args.video_id):
        raise RuntimeError("Video is still present after waiting for YouTube deletion propagation")
    print("deleted=" + args.video_id)
    return 0


def set_privacy(video_id, privacy):
    current = g.api_json("https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode({
        "part": "status", "id": video_id
    })).get("items", [])
    if len(current) != 1:
        raise RuntimeError("Video not found")
    status = current[0].get("status", {}); status["privacyStatus"] = privacy
    token, _ = g.access_token()
    response = requests.put("https://www.googleapis.com/youtube/v3/videos", params={"part": "status"},
                            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
                            data=json.dumps({"id": video_id, "status": status}), timeout=60)
    response.raise_for_status()
    actual = response.json().get("status", {}).get("privacyStatus")
    if actual != privacy:
        raise RuntimeError(f"YouTube returned privacy {actual!r}, expected {privacy!r}")
    return actual

def privacy_cmd(args):
    print("privacy=" + str(set_privacy(args.video_id, args.privacy)))
    return 0


def self_test_cmd(_args):
    vid = None
    with tempfile.TemporaryDirectory(prefix="youtube-api-test-", dir="/data/tmp") as temp:
        path = Path(temp) / "test.mp4"
        subprocess.run(["/usr/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=black:s=320x240:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True, timeout=60)
        try:
            result = upload_file(path, "Multiverse Services automated API self-test",
                                 "Temporary private verification video; deleted automatically.", "private", "22")
            vid = result["id"]
            check = g.api_json("https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode({
                "part": "id,snippet,status", "id": vid
            })).get("items", [])
            if len(check) != 1 or check[0].get("status", {}).get("privacyStatus") != "private":
                raise RuntimeError("Private upload verification failed")
            print("upload=OK")
            if set_privacy(vid, "unlisted") != "unlisted":
                raise RuntimeError("Unlisted privacy transition failed")
            if set_privacy(vid, "private") != "private":
                raise RuntimeError("Private privacy transition failed")
            print("privacy_transitions=OK")
        finally:
            if vid:
                delete_video(vid)
                if not wait_deleted(vid):
                    raise RuntimeError("Temporary YouTube test video was not deleted after propagation wait")
                print("delete=OK")
    return 0


def main():
    parser = argparse.ArgumentParser(description="YouTube operations for the Multiverse Google account")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("channel"); p.set_defaults(func=channel_cmd)
    p = sub.add_parser("list"); p.add_argument("--limit", type=int, default=20); p.set_defaults(func=list_cmd)
    p = sub.add_parser("upload"); p.add_argument("file"); p.add_argument("--title", required=True); p.add_argument("--description", default=""); p.add_argument("--privacy", choices=("private", "unlisted", "public"), default="private"); p.add_argument("--category", default="22"); p.set_defaults(func=upload_cmd)
    p = sub.add_parser("delete"); p.add_argument("video_id"); p.set_defaults(func=delete_cmd)
    p = sub.add_parser("privacy"); p.add_argument("video_id"); p.add_argument("privacy", choices=("private", "unlisted", "public")); p.set_defaults(func=privacy_cmd)
    p = sub.add_parser("self-test"); p.set_defaults(func=self_test_cmd)
    args = parser.parse_args(); return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
