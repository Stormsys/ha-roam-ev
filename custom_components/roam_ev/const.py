"""Constants for ROAM EV Charging integration."""

DOMAIN = "roam_ev"

# Firebase/Google configuration
FIREBASE_API_KEY = "AIzaSyD4j5oEpmxNpjc5_sdObpQF0Pf2sk0b0LA"
FIRESTORE_PROJECT_ID = "prod-evc-app"
API_BASE_URL = "europe-west2-prod-evc-app.cloudfunctions.net"

# API endpoints
FIREBASE_AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
FIREBASE_REFRESH_URL = "https://securetoken.googleapis.com/v1/token"
FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/users/{user_id}"
CHARGER_URL = "https://{base}/evc_charge/charger/{charger_id}"

# Config keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_USER_ID = "user_id"
CONF_ID_TOKEN = "id_token"
CONF_TOKEN_EXPIRY = "token_expiry"

# Update interval in seconds
DEFAULT_SCAN_INTERVAL = 30

# Platforms
PLATFORMS = ["binary_sensor", "sensor"]

