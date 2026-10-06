<?php
/**
 * Require the existing Raspi administrator session on every dynamic mail request.
 * The signing secret remains readable only by the loopback verifier process.
 */
class portal_mail extends rcube_plugin
{
    private $portal_sid;
    public function init()
    {
        $cookie = $_SERVER['HTTP_COOKIE'] ?? '';
        if (preg_match('/[\r\n]/', $cookie)) {
            http_response_code(403); exit;
        }
        $rc = rcmail::get_instance();
        $url = $rc->config->get('portal_mail_auth_url');
        $context = stream_context_create(['http' => [
            'method' => 'GET', 'timeout' => 3, 'ignore_errors' => true,
            'follow_location' => 0, 'header' => "Cookie: " . $cookie . "\r\n"
        ]]);
        $result = @file_get_contents($url, false, $context);
        $status = $http_response_header[0] ?? '';
        $auth = json_decode($result ?: '{}', true);
        if (!preg_match('/^HTTP\/\S+ 200\b/', $status) || empty($auth['ok']) || empty($auth['sid'])) {
            if (!empty($_SESSION['user_id'])) { $rc->kill_session(); }
            header('Cache-Control: no-store');
            header('Location: /', true, 303);
            exit;
        }
        $this->portal_sid = $auth['sid'];
        if (!empty($_SESSION['portal_mail_sid']) && !hash_equals($_SESSION['portal_mail_sid'], $this->portal_sid)) {
            $rc->kill_session();
        }
        $this->add_hook('startup', [$this, 'startup']);
        $this->add_hook('authenticate', [$this, 'authenticate']);
        $this->add_hook('login_after', [$this, 'after_login']);
        $this->add_hook('user_create', [$this, 'user_create']);
        $this->add_hook('message_before_send', [$this, 'before_send']);
    }
    public function startup($args)
    {
        if (empty($_SESSION['user_id'])) {
            $args['task'] = 'login';
            $args['action'] = 'login';
        }
        return $args;
    }
    public function authenticate($args)
    {
        $rc = rcmail::get_instance();
        $args['host'] = '127.0.0.1:' . $rc->config->get('portal_mail_imap_port');
        $args['user'] = $rc->config->get('portal_mail_account');
        $args['pass'] = trim(file_get_contents('/data/var/mail/secrets/local-password'));
        $args['valid'] = true;
        $args['cookiecheck'] = false;
        $args['abort'] = false;
        return $args;
    }
    public function after_login($args)
    {
        $_SESSION['portal_mail_sid'] = $this->portal_sid;
        return $args;
    }
    public function user_create($args)
    {
        $args['user_name'] = 'Multiverse';
        $args['user_email'] = rcmail::get_instance()->config->get('portal_mail_account');
        return $args;
    }
    public function before_send($args)
    {
        $socket = @stream_socket_client('tcp://127.0.0.1:16202', $errno, $errstr, 1);
        if (!$socket) {
            $args['abort'] = true;
            $args['error'] = 'Local OAuth mail sender is unavailable.';
        } else {
            fclose($socket);
        }
        return $args;
    }
}
