import httpx
from openai import OpenAI
from oci_genai_auth import OciInstancePrincipalAuth, OciSessionAuth

from config import AUTH_MODE, BASE_URL, OCI_CONFIG_PROFILE, PROJECT_ID


def build_auth():
    if AUTH_MODE == "session":
        return OciSessionAuth(profile_name=OCI_CONFIG_PROFILE)
    return OciInstancePrincipalAuth()


client = OpenAI(
    base_url=BASE_URL,
    api_key="not-used",
    project=PROJECT_ID,
    http_client=httpx.Client(auth=build_auth()),
)
