from postmarker.core import PostmarkClient  # pylint: disable=import-error
from config import Config

# Initialize the Postmark Client
postmark = PostmarkClient(server_token=Config.POSTMARK_API_KEY)
