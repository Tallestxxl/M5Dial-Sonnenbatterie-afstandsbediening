#pragma once

// Copy this file to sonnen_config.h and fill in your own values.

static const char WIFI_SSID[] = "YOUR_WIFI_SSID";
static const char WIFI_PASSWORD[] = "YOUR_WIFI_PASSWORD";

// Local sonnenBatterie host or IP address. Keep this on your trusted LAN.
static const char SONNEN_HOST[] = "192.168.1.50";
static const uint16_t SONNEN_PORT = 80;
static const char SONNEN_AUTH_HEADER[] = "Auth-Token";
static const char SONNEN_AUTH_TOKEN[] = "";

// Set to 1 to test display, encoder, button, dimming and sleep without Wi-Fi
// or a sonnenBatterie. Keep this 0 for real operation.
#define SONNEN_DEMO_MODE 0

// Defaults match the commonly used local sonnen API v2 shape. If your unit
// exposes different paths or verbs, change them here instead of in the sketch.
#define SONNEN_STATUS_PATH "/api/v2/status"
#define SONNEN_CONFIGURATION_PATH "/api/v2/configurations"
#define SONNEN_CHARGE_SETPOINT_PATH "/api/v2/setpoint/charge"
#define SONNEN_DISCHARGE_SETPOINT_PATH "/api/v2/setpoint/discharge"

// Keep writes disabled for the first bring-up. Set to 1 only after STATUS works
// and you have confirmed the API paths/modes for your exact sonnenBatterie.
#define SONNEN_ALLOW_WRITES 0
#define SONNEN_CONFIG_METHOD "PUT"
#define SONNEN_SETPOINT_METHOD "POST"
#define SONNEN_SELF_CONSUMPTION_BODY "{\"EM_OperatingMode\":\"2\"}"
#define SONNEN_MANUAL_MODE_BODY "{\"EM_OperatingMode\":\"1\"}"
#define SONNEN_SETPOINT_BODY ""
#define SONNEN_ENABLE_MANUAL_BEFORE_SETPOINT 1

#define SONNEN_DEFAULT_SETPOINT_W 500
#define SONNEN_MAX_SETPOINT_W 3600
#define SONNEN_SETPOINT_STEP_W 100

#define SONNEN_WIFI_TIMEOUT_MS 9000
#define SONNEN_HTTP_TIMEOUT_MS 4500
#define SONNEN_WIFI_OFF_AFTER_REQUEST 1
#define SONNEN_STATUS_REFRESH_MS 15000
#define SONNEN_ACTIVE_REFRESH_MS 10000
#define SONNEN_IDLE_REFRESH_MS 60000
#define SONNEN_ERROR_REFRESH_MS 20000
#define SONNEN_ACTIVE_POWER_THRESHOLD_W 100
// Set dim or sleep to 0 to disable that automatic power policy.
#define SONNEN_DIM_AFTER_MS 20000
#define SONNEN_SLEEP_AFTER_MS 70000
#define SONNEN_ENABLE_POWER_OFF 0
#define SONNEN_ACTIVE_BRIGHTNESS 96
#define SONNEN_DIM_BRIGHTNESS 18
