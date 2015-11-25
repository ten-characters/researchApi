# #!/home/ubuntu/api/api_env/bin/python

__author__ = 'austin'
from APP import app as api


if __name__ == "__main__":
    api.run(port=5000)
