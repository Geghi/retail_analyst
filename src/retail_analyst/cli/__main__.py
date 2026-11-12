import sys

from dotenv import load_dotenv

from .startup import main

load_dotenv()
sys.exit(main(sys.argv[1:]))
