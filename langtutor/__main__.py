import os
import sys
import json
import yaml
import signal
import argparse



def exit_graceful(signum, frame) -> None:
    """
    Stop threads when app terminates.

    :param signum: required by `signal.signal`
    :param frame: required by `signal.signal`
    """
    
    sys.exit(0)



def main():

    parser = argparse.ArgumentParser()

    signal.signal(signal.SIGINT, exit_graceful)
    signal.signal(signal.SIGTERM, exit_graceful)
    
    from .app import app
    app.run("0.0.0.0")


if __name__ == '__main__':
    main()