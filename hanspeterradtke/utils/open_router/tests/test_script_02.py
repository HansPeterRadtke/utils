def calculate():
    # Another intentional error: undefined variable
    result = foo + 1
    return result

if __name__ == "__main__":
    print(calculate())