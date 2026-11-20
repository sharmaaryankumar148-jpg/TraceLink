# In-memory redis for local dev (redis isn't easy to install on windows).
# usage: python scripts/dev_redis.py
from fakeredis import TcpFakeServer

if __name__ == "__main__":
    address = ("127.0.0.1", 6379)
    server = TcpFakeServer(address, server_type="redis")
    print(f"Fake redis on {address[0]}:{address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
