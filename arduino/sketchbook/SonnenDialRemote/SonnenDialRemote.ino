#include <Arduino.h>
#include <HTTPClient.h>
#include <M5Dial.h>
#include <WiFi.h>

#if __has_include("sonnen_config.h")
#include "sonnen_config.h"
#else
#include "config.example.h"
#endif

#ifndef SONNEN_STATUS_REFRESH_MS
#define SONNEN_STATUS_REFRESH_MS 15000
#endif

#ifndef SONNEN_ACTIVE_REFRESH_MS
#define SONNEN_ACTIVE_REFRESH_MS SONNEN_STATUS_REFRESH_MS
#endif

#ifndef SONNEN_IDLE_REFRESH_MS
#define SONNEN_IDLE_REFRESH_MS 60000
#endif

#ifndef SONNEN_ERROR_REFRESH_MS
#define SONNEN_ERROR_REFRESH_MS 20000
#endif

#ifndef SONNEN_ACTIVE_POWER_THRESHOLD_W
#define SONNEN_ACTIVE_POWER_THRESHOLD_W 100
#endif

#ifndef SONNEN_DIM_AFTER_MS
#define SONNEN_DIM_AFTER_MS 20000
#endif

#ifndef SONNEN_SLEEP_AFTER_MS
#define SONNEN_SLEEP_AFTER_MS 70000
#endif

#ifndef SONNEN_ACTIVE_BRIGHTNESS
#define SONNEN_ACTIVE_BRIGHTNESS 96
#endif

#ifndef SONNEN_DIM_BRIGHTNESS
#define SONNEN_DIM_BRIGHTNESS 18
#endif

#ifndef SONNEN_WIFI_OFF_AFTER_REQUEST
#define SONNEN_WIFI_OFF_AFTER_REQUEST 1
#endif

#ifndef SONNEN_ALLOW_WRITES
#define SONNEN_ALLOW_WRITES 0
#endif

#ifndef SONNEN_DEMO_MODE
#define SONNEN_DEMO_MODE 0
#endif

#ifndef SONNEN_ENABLE_POWER_OFF
#define SONNEN_ENABLE_POWER_OFF 0
#endif

enum class Action : uint8_t {
  Refresh = 0,
  SelfConsumption,
  Charge,
  Discharge,
  Sleep,
};

enum class UiState : uint8_t {
  Browsing,
  EditingSetpoint,
  Busy,
  Error,
};

struct BatteryStatus {
  bool valid = false;
  int soc = 0;
  long productionW = 0;
  long consumptionW = 0;
  long gridW = 0;
  long batteryW = 0;
  String operatingMode = "?";
  String timestamp = "";
  String lastError = "";
};

struct ApiResult {
  bool ok = false;
  int code = 0;
  String payload = "";
  String message = "";
};

static constexpr int kActionCount = 5;
static constexpr uint32_t kLongPressMs = 1200;
static constexpr float kDegToRad = 0.01745329252f;

static BatteryStatus battery;
static UiState uiState = UiState::Browsing;
static Action selectedAction = Action::Refresh;
static int requestedPowerW = SONNEN_DEFAULT_SETPOINT_W;
static long lastEncoderPosition = 0;
static bool buttonDown = false;
static bool longPressHandled = false;
static bool displayDimmed = false;
static uint32_t buttonDownAtMs = 0;
static uint32_t lastInteractionMs = 0;
static uint32_t lastRefreshMs = 0;
static uint32_t lastSuccessfulRefreshMs = 0;
static uint32_t stateStartedMs = 0;
static String statusMessage = "Starting";

static uint16_t colBg;
static uint16_t colPanel;
static uint16_t colText;
static uint16_t colMuted;
static uint16_t colGood;
static uint16_t colWarn;
static uint16_t colBad;
static uint16_t colBlue;

static int clampPower(int value) {
  value = constrain(value, 0, SONNEN_MAX_SETPOINT_W);
  int step = max(1, SONNEN_SETPOINT_STEP_W);
  return (value / step) * step;
}

static const char *actionLabel(Action action) {
  switch (action) {
    case Action::Refresh:
      return "STATUS";
    case Action::SelfConsumption:
      return "AUTO";
    case Action::Charge:
      return "CHARGE";
    case Action::Discharge:
      return "DISCH";
    case Action::Sleep:
#if SONNEN_ENABLE_POWER_OFF
      return "SLEEP";
#else
      return "DIM";
#endif
  }
  return "?";
}

static Action actionFromIndex(int index) {
  index %= kActionCount;
  if (index < 0) {
    index += kActionCount;
  }
  return static_cast<Action>(index);
}

static int actionIndex(Action action) {
  return static_cast<int>(action);
}

static String fitText(const String &text, size_t maxLen) {
  if (text.length() <= maxLen) {
    return text;
  }
  if (maxLen < 2) {
    return text.substring(0, maxLen);
  }
  return text.substring(0, maxLen - 1) + ".";
}

static String signedWatts(long watts) {
  char buffer[18];
  if (watts > 0) {
    snprintf(buffer, sizeof(buffer), "+%ldW", watts);
  } else {
    snprintf(buffer, sizeof(buffer), "%ldW", watts);
  }
  return String(buffer);
}

static String batteryWattsForDisplay() {
  // Sonnen reports Pac_total_W as positive when discharging; the UI shows
  // positive when energy flows into the battery.
  return signedWatts(-battery.batteryW);
}

static bool batteryPowerIsActive() {
  if (!battery.valid) {
    return true;
  }
  long watts = battery.batteryW;
  if (watts < 0) {
    watts = -watts;
  }
  return watts >= SONNEN_ACTIVE_POWER_THRESHOLD_W;
}

static uint32_t currentRefreshIntervalMs() {
  if (!battery.valid || batteryPowerIsActive()) {
    return SONNEN_ACTIVE_REFRESH_MS;
  }
  return SONNEN_IDLE_REFRESH_MS;
}

static uint16_t statusColor() {
  if (uiState == UiState::Error) {
    return colBad;
  }
  if (uiState == UiState::Busy) {
    return colWarn;
  }
  if (selectedAction == Action::Charge || selectedAction == Action::Discharge) {
    return colBlue;
  }
  return colGood;
}

static void noteInteraction() {
  lastInteractionMs = millis();
  if (displayDimmed) {
    M5Dial.Display.setBrightness(SONNEN_ACTIVE_BRIGHTNESS);
    displayDimmed = false;
  }
}

static void drawRing(int cx, int cy, int radius, int pct, uint16_t activeColor) {
  pct = constrain(pct, 0, 100);
  int activeTicks = map(pct, 0, 100, 0, 60);
  for (int i = 0; i < 60; ++i) {
    float angle = (-220.0f + (260.0f * i / 59.0f)) * kDegToRad;
    int inner = radius - ((i % 5 == 0) ? 11 : 7);
    int outer = radius;
    int x1 = cx + static_cast<int>(cosf(angle) * inner);
    int y1 = cy + static_cast<int>(sinf(angle) * inner);
    int x2 = cx + static_cast<int>(cosf(angle) * outer);
    int y2 = cy + static_cast<int>(sinf(angle) * outer);
    M5Dial.Display.drawLine(x1, y1, x2, y2, i < activeTicks ? activeColor : colPanel);
  }
}

static void drawMetric(int x, int y, const char *label, const String &value, uint16_t color) {
  M5Dial.Display.setTextDatum(middle_center);
  M5Dial.Display.setTextColor(colMuted);
  M5Dial.Display.setTextSize(1);
  M5Dial.Display.drawString(label, x, y);
  M5Dial.Display.setTextColor(color);
  M5Dial.Display.setTextSize(2);
  M5Dial.Display.drawString(value, x, y + 16);
}

static void drawFooter() {
  uint16_t accent = statusColor();
  M5Dial.Display.fillRoundRect(34, 211, 172, 24, 7, accent);
  M5Dial.Display.setTextDatum(middle_center);
  M5Dial.Display.setTextColor(colBg);

  if (uiState == UiState::EditingSetpoint) {
    M5Dial.Display.setTextSize(1);
    M5Dial.Display.drawString("TURN W  PRESS OK", 120, 223);
    return;
  }
  if (uiState == UiState::Busy) {
    M5Dial.Display.setTextSize(2);
    M5Dial.Display.drawString("WORKING", 120, 223);
    return;
  }
  if (uiState == UiState::Error) {
    M5Dial.Display.setTextSize(1);
    M5Dial.Display.drawString("PRESS TO RETRY", 120, 223);
    return;
  }

  String label = String("< ") + actionLabel(selectedAction) + " >";
  M5Dial.Display.setTextSize(2);
  M5Dial.Display.drawString(label, 120, 223);
}

static void drawUi() {
  M5Dial.Display.fillScreen(colBg);
  M5Dial.Display.setTextDatum(middle_center);

  uint16_t ringColor = statusColor();
  int displaySoc = battery.valid ? battery.soc : 0;
  drawRing(120, 103, 82, displaySoc, ringColor);

  M5Dial.Display.setTextSize(1);
  M5Dial.Display.setTextColor(statusColor());
  M5Dial.Display.drawString(fitText(statusMessage, 24), 120, 49);

  M5Dial.Display.setTextDatum(middle_center);
  if (uiState == UiState::EditingSetpoint) {
    M5Dial.Display.setTextColor(colText);
    M5Dial.Display.setTextSize(3);
    M5Dial.Display.drawString(String(requestedPowerW), 120, 94);
    M5Dial.Display.setTextSize(1);
    M5Dial.Display.setTextColor(colMuted);
    M5Dial.Display.drawString("WATT", 120, 121);
  } else {
    M5Dial.Display.setTextColor(colText);
    M5Dial.Display.setTextSize(4);
    M5Dial.Display.drawString(battery.valid ? String(battery.soc) : "--", 111, 96);
    M5Dial.Display.setTextSize(2);
    M5Dial.Display.drawString("%", 163, 101);
    M5Dial.Display.setTextSize(1);
    M5Dial.Display.setTextColor(colMuted);
    M5Dial.Display.drawString("SOC", 120, 126);
  }

  drawMetric(60, 150, "PV", battery.valid ? signedWatts(battery.productionW) : "--", colGood);
  drawMetric(180, 150, "USE", battery.valid ? signedWatts(battery.consumptionW) : "--", colText);
  drawMetric(60, 183, "GRID", battery.valid ? signedWatts(battery.gridW) : "--", colWarn);
  drawMetric(180, 183, "BAT", battery.valid ? batteryWattsForDisplay() : "--", colBlue);

  drawFooter();
}

static String baseUrl() {
  String host = SONNEN_HOST;
  String url;
  if (host.startsWith("http://") || host.startsWith("https://")) {
    url = host;
  } else {
    url = "http://" + host;
  }

  int schemeEnd = url.indexOf("://");
  int hostStart = schemeEnd >= 0 ? schemeEnd + 3 : 0;
  bool urlAlreadyHasPort = url.indexOf(':', hostStart) >= 0;
  if (SONNEN_PORT != 80 && !urlAlreadyHasPort) {
    url += ":" + String(SONNEN_PORT);
  }
  return url;
}

static String urlForPath(const String &path) {
  String url = baseUrl();
  if (!path.startsWith("/")) {
    url += "/";
  }
  url += path;
  return url;
}

static bool ensureWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  statusMessage = "Wi-Fi";
  drawUi();

  WiFi.mode(WIFI_STA);
  WiFi.persistent(false);
  WiFi.setSleep(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < SONNEN_WIFI_TIMEOUT_MS) {
    M5Dial.update();
    delay(80);
  }

  if (WiFi.status() != WL_CONNECTED) {
    battery.lastError = "Wi-Fi timeout";
#if SONNEN_WIFI_OFF_AFTER_REQUEST
    WiFi.disconnect(false);
    WiFi.mode(WIFI_OFF);
#endif
    return false;
  }
  return true;
}

static void releaseWiFiAfterRequest() {
#if SONNEN_WIFI_OFF_AFTER_REQUEST
  WiFi.disconnect(false);
  WiFi.mode(WIFI_OFF);
#endif
}

static ApiResult requestSonnen(const char *method,
                               const String &path,
                               const String &body = "",
                               const char *contentType = "application/json",
                               bool releaseWiFi = true) {
  ApiResult result;
  if (!ensureWiFi()) {
    result.message = battery.lastError;
    return result;
  }

  WiFiClient client;
  HTTPClient http;
  String url = urlForPath(path);

  if (!http.begin(client, url)) {
    result.message = "HTTP begin failed";
    if (releaseWiFi) {
      releaseWiFiAfterRequest();
    }
    return result;
  }

  http.setTimeout(SONNEN_HTTP_TIMEOUT_MS);
  if (strlen(SONNEN_AUTH_TOKEN) > 0) {
    http.addHeader(SONNEN_AUTH_HEADER, SONNEN_AUTH_TOKEN);
  }
  if (body.length() > 0 && contentType != nullptr && strlen(contentType) > 0) {
    http.addHeader("Content-Type", contentType);
  }

  String methodName(method);
  methodName.toUpperCase();

  if (methodName == "GET") {
    result.code = http.GET();
  } else if (methodName == "POST") {
    result.code = http.POST(body);
  } else if (methodName == "PUT") {
    result.code = http.PUT(body);
  } else if (methodName == "PATCH") {
    result.code = http.PATCH(body);
  } else {
    result.message = "Bad HTTP method";
    http.end();
    if (releaseWiFi) {
      releaseWiFiAfterRequest();
    }
    return result;
  }

  result.payload = http.getString();
  http.end();
  if (releaseWiFi) {
    releaseWiFiAfterRequest();
  }

  result.ok = result.code >= 200 && result.code < 300;
  if (!result.ok) {
    result.message = "HTTP " + String(result.code);
  }
  return result;
}

static int jsonValueStart(const String &payload, const char *key) {
  String needle = "\"" + String(key) + "\"";
  int keyPos = payload.indexOf(needle);
  if (keyPos < 0) {
    return -1;
  }

  int colonPos = payload.indexOf(':', keyPos + needle.length());
  if (colonPos < 0) {
    return -1;
  }

  int pos = colonPos + 1;
  while (pos < static_cast<int>(payload.length()) && isspace(static_cast<unsigned char>(payload[pos]))) {
    ++pos;
  }
  return pos < static_cast<int>(payload.length()) ? pos : -1;
}

static bool readJsonLong(const String &payload, const char *key, long &value) {
  int pos = jsonValueStart(payload, key);
  if (pos < 0) {
    return false;
  }

  if (payload[pos] == '"') {
    ++pos;
  }

  int start = pos;
  if (payload[pos] == '-' || payload[pos] == '+') {
    ++pos;
  }

  bool hasDigit = false;
  while (pos < static_cast<int>(payload.length()) && isdigit(static_cast<unsigned char>(payload[pos]))) {
    hasDigit = true;
    ++pos;
  }

  if (!hasDigit) {
    return false;
  }

  value = payload.substring(start, pos).toInt();
  return true;
}

static bool readAnyJsonLong(const String &payload,
                            long &value,
                            const char *keyA,
                            const char *keyB = nullptr,
                            const char *keyC = nullptr) {
  const char *keys[] = {keyA, keyB, keyC};
  for (const char *key : keys) {
    if (key != nullptr && readJsonLong(payload, key, value)) {
      return true;
    }
  }
  return false;
}

static String readJsonString(const String &payload, const char *key, const String &fallback) {
  int pos = jsonValueStart(payload, key);
  if (pos < 0) {
    return fallback;
  }

  if (payload[pos] == '"') {
    String value;
    ++pos;
    while (pos < static_cast<int>(payload.length())) {
      char c = payload[pos++];
      if (c == '"') {
        return value;
      }
      if (c == '\\' && pos < static_cast<int>(payload.length())) {
        value += payload[pos++];
      } else {
        value += c;
      }
    }
    return fallback;
  }

  int end = pos;
  while (end < static_cast<int>(payload.length()) && payload[end] != ',' && payload[end] != '}') {
    ++end;
  }
  String value = payload.substring(pos, end);
  value.trim();
  return value.length() ? value : fallback;
}

static String readAnyJsonString(const String &payload,
                                const String &fallback,
                                const char *keyA,
                                const char *keyB = nullptr,
                                const char *keyC = nullptr) {
  const char *keys[] = {keyA, keyB, keyC};
  for (const char *key : keys) {
    if (key == nullptr) {
      continue;
    }
    String value = readJsonString(payload, key, "");
    if (value.length()) {
      return value;
    }
  }
  return fallback;
}

static bool parseStatus(const String &payload) {
  long value = 0;
  if (!readAnyJsonLong(payload, value, "USOC", "RSOC", "RelativeStateOfCharge")) {
    battery.lastError = "SOC missing";
    return false;
  }
  battery.soc = constrain(static_cast<int>(value), 0, 100);

  if (readAnyJsonLong(payload, value, "Production_W", "ProductionW", "PV_Production_W")) {
    battery.productionW = value;
  } else {
    battery.productionW = 0;
  }

  if (readAnyJsonLong(payload, value, "Consumption_W", "Consumption_Avg", "ConsumptionW")) {
    battery.consumptionW = value;
  } else {
    battery.consumptionW = 0;
  }

  if (readAnyJsonLong(payload, value, "GridFeedIn_W", "GridFeedIn", "GridFeedInW")) {
    battery.gridW = value;
  } else {
    battery.gridW = 0;
  }

  if (readAnyJsonLong(payload, value, "Pac_total_W", "BatteryPower_W", "Battery_W")) {
    battery.batteryW = value;
  } else {
    battery.batteryW = 0;
  }

  battery.operatingMode = readAnyJsonString(payload, "?", "OperatingMode", "EM_OperatingMode", "Mode");
  battery.timestamp = readAnyJsonString(payload, "", "Timestamp", "System_Time", "timestamp");
  battery.valid = true;
  battery.lastError = "";
  return true;
}

static void populateDemoStatus() {
  long phase = (millis() / 1200) % 100;
  battery.soc = constrain(static_cast<int>(42 + (phase % 37)), 0, 100);
  battery.productionW = 850 + ((phase * 37) % 1800);
  battery.consumptionW = 320 + ((phase * 23) % 900);
  battery.gridW = battery.consumptionW - battery.productionW;
  battery.batteryW = -battery.gridW / 2;
  battery.operatingMode = "DEMO";
  battery.timestamp = String(millis() / 1000) + "s";
  battery.valid = true;
  battery.lastError = "";
}

static bool refreshStatus(bool showBusy = true, bool releaseWiFi = true) {
  UiState previousState = uiState;
  if (showBusy) {
    uiState = UiState::Busy;
    statusMessage = "Reading";
    drawUi();
  }

#if SONNEN_DEMO_MODE
  populateDemoStatus();
  lastRefreshMs = millis();
  lastSuccessfulRefreshMs = lastRefreshMs;
  uiState = (previousState == UiState::Busy || previousState == UiState::Error) ? UiState::Browsing : previousState;
  statusMessage = "Demo mode";
  drawUi();
  return true;
#endif

  ApiResult result = requestSonnen("GET", SONNEN_STATUS_PATH, "", "application/json", releaseWiFi);
  lastRefreshMs = millis();

  if (!result.ok) {
    uiState = UiState::Error;
    statusMessage = fitText(result.message.length() ? result.message : "Status failed", 24);
    stateStartedMs = millis();
    drawUi();
    return false;
  }

  if (!parseStatus(result.payload)) {
    uiState = UiState::Error;
    statusMessage = battery.lastError;
    stateStartedMs = millis();
    drawUi();
    return false;
  }

  lastSuccessfulRefreshMs = millis();
  uiState = (previousState == UiState::Busy || previousState == UiState::Error) ? UiState::Browsing : previousState;
  statusMessage = "Mode " + battery.operatingMode;
  drawUi();
  return true;
}

static String setpointPath(bool charge) {
  String path = charge ? SONNEN_CHARGE_SETPOINT_PATH : SONNEN_DISCHARGE_SETPOINT_PATH;
  if (!path.endsWith("/")) {
    path += "/";
  }
  path += String(requestedPowerW);
  return path;
}

static bool putSelfConsumption() {
#if SONNEN_DEMO_MODE
  uiState = UiState::Error;
  statusMessage = "Demo only";
  battery.lastError = "SONNEN_DEMO_MODE=1";
  stateStartedMs = millis();
  drawUi();
  return false;
#endif

#if !SONNEN_ALLOW_WRITES
  uiState = UiState::Error;
  statusMessage = "Writes locked";
  battery.lastError = "SONNEN_ALLOW_WRITES=0";
  stateStartedMs = millis();
  drawUi();
  return false;
#endif

  uiState = UiState::Busy;
  statusMessage = "Auto mode";
  drawUi();

  ApiResult result = requestSonnen(SONNEN_CONFIG_METHOD,
                                   SONNEN_CONFIGURATION_PATH,
                                   SONNEN_SELF_CONSUMPTION_BODY,
                                   "application/json",
                                   false);
  if (!result.ok) {
    releaseWiFiAfterRequest();
    uiState = UiState::Error;
    statusMessage = fitText(result.message.length() ? result.message : "Auto failed", 24);
    stateStartedMs = millis();
    drawUi();
    return false;
  }

  uiState = UiState::Browsing;
  statusMessage = "Auto OK";
  refreshStatus(false);
  return true;
}

static bool sendSetpoint(bool charge) {
#if SONNEN_DEMO_MODE
  uiState = UiState::Error;
  statusMessage = "Demo only";
  battery.lastError = "SONNEN_DEMO_MODE=1";
  stateStartedMs = millis();
  drawUi();
  return false;
#endif

#if !SONNEN_ALLOW_WRITES
  uiState = UiState::Error;
  statusMessage = "Writes locked";
  battery.lastError = "SONNEN_ALLOW_WRITES=0";
  stateStartedMs = millis();
  drawUi();
  return false;
#endif

  uiState = UiState::Busy;
  statusMessage = charge ? "Charging" : "Discharging";
  drawUi();

#if SONNEN_ENABLE_MANUAL_BEFORE_SETPOINT
  ApiResult mode = requestSonnen(SONNEN_CONFIG_METHOD,
                                 SONNEN_CONFIGURATION_PATH,
                                 SONNEN_MANUAL_MODE_BODY,
                                 "application/json",
                                 false);
  if (!mode.ok) {
    releaseWiFiAfterRequest();
    uiState = UiState::Error;
    statusMessage = fitText(mode.message.length() ? mode.message : "Manual failed", 24);
    stateStartedMs = millis();
    drawUi();
    return false;
  }
  delay(200);
#endif

  ApiResult result = requestSonnen(SONNEN_SETPOINT_METHOD,
                                   setpointPath(charge),
                                   SONNEN_SETPOINT_BODY,
                                   "application/json",
                                   false);
  if (!result.ok) {
    releaseWiFiAfterRequest();
    uiState = UiState::Error;
    statusMessage = fitText(result.message.length() ? result.message : "Setpoint failed", 24);
    stateStartedMs = millis();
    drawUi();
    return false;
  }

  uiState = UiState::Browsing;
  statusMessage = String(charge ? "Charge " : "Disch ") + requestedPowerW + "W";
  refreshStatus(false);
  return true;
}

static void powerOff() {
#if SONNEN_ENABLE_POWER_OFF
  uiState = UiState::Busy;
  statusMessage = "Sleeping";
  drawUi();
  delay(250);
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  M5Dial.Display.setBrightness(0);
  M5Dial.Power.powerOff();
#else
  M5Dial.Display.setBrightness(SONNEN_DIM_BRIGHTNESS);
  displayDimmed = true;
  statusMessage = "Dimmed";
  drawUi();
#endif
}

static void handleShortPress() {
  noteInteraction();

  if (uiState == UiState::Busy) {
    return;
  }

  if (uiState == UiState::Error) {
    uiState = UiState::Browsing;
    refreshStatus(true);
    return;
  }

  if (uiState == UiState::EditingSetpoint) {
    bool charge = selectedAction == Action::Charge;
    sendSetpoint(charge);
    return;
  }

  switch (selectedAction) {
    case Action::Refresh:
      refreshStatus(true);
      break;
    case Action::SelfConsumption:
      putSelfConsumption();
      break;
    case Action::Charge:
    case Action::Discharge:
      uiState = UiState::EditingSetpoint;
      statusMessage = selectedAction == Action::Charge ? "Charge W" : "Disch W";
      stateStartedMs = millis();
      drawUi();
      break;
    case Action::Sleep:
      powerOff();
      break;
  }
}

static void handleLongPress() {
  noteInteraction();
  if (uiState == UiState::EditingSetpoint || uiState == UiState::Error) {
    uiState = UiState::Browsing;
    statusMessage = "Cancelled";
    drawUi();
    return;
  }
  powerOff();
}

static void handleEncoder() {
  long position = M5Dial.Encoder.read();
  long delta = position - lastEncoderPosition;
  if (delta == 0 || uiState == UiState::Busy) {
    return;
  }

  lastEncoderPosition = position;
  noteInteraction();

  if (uiState == UiState::EditingSetpoint) {
    requestedPowerW = clampPower(requestedPowerW + static_cast<int>(delta) * SONNEN_SETPOINT_STEP_W);
    statusMessage = selectedAction == Action::Charge ? "Charge W" : "Disch W";
    drawUi();
    return;
  }

  if (uiState == UiState::Error) {
    uiState = UiState::Browsing;
  }

  selectedAction = actionFromIndex(actionIndex(selectedAction) + static_cast<int>(delta));
  statusMessage = actionLabel(selectedAction);
  drawUi();
}

static void handleButton() {
  if (M5Dial.BtnA.wasPressed()) {
    buttonDown = true;
    longPressHandled = false;
    buttonDownAtMs = millis();
  }

  if (buttonDown && !longPressHandled && M5Dial.BtnA.pressedFor(kLongPressMs)) {
    longPressHandled = true;
    buttonDown = false;
    handleLongPress();
  }

  if (M5Dial.BtnA.wasReleased()) {
    if (buttonDown && !longPressHandled && millis() - buttonDownAtMs < kLongPressMs) {
      handleShortPress();
    }
    buttonDown = false;
    longPressHandled = false;
  }
}

static void maintainPowerPolicy() {
  uint32_t idle = millis() - lastInteractionMs;

  if (SONNEN_SLEEP_AFTER_MS > 0 && idle > SONNEN_SLEEP_AFTER_MS) {
    powerOff();
    return;
  }

  if (SONNEN_DIM_AFTER_MS > 0 && !displayDimmed && idle > SONNEN_DIM_AFTER_MS) {
    M5Dial.Display.setBrightness(SONNEN_DIM_BRIGHTNESS);
    displayDimmed = true;
  }
}

static void maybeRefreshStatus() {
  if (uiState == UiState::Busy || uiState == UiState::EditingSetpoint) {
    return;
  }

  uint32_t interval = uiState == UiState::Error ? SONNEN_ERROR_REFRESH_MS : currentRefreshIntervalMs();
  if (millis() - lastRefreshMs < interval) {
    return;
  }
  refreshStatus(false);
}

static void setupPalette() {
  colBg = M5Dial.Display.color565(8, 12, 16);
  colPanel = M5Dial.Display.color565(42, 49, 55);
  colText = M5Dial.Display.color565(235, 239, 232);
  colMuted = M5Dial.Display.color565(142, 151, 151);
  colGood = M5Dial.Display.color565(75, 207, 139);
  colWarn = M5Dial.Display.color565(240, 171, 67);
  colBad = M5Dial.Display.color565(232, 91, 82);
  colBlue = M5Dial.Display.color565(83, 169, 232);
}

void setup() {
  auto cfg = M5.config();
  M5Dial.begin(cfg, true, false);
  M5Dial.Display.setRotation(3);
  setupPalette();

  requestedPowerW = clampPower(requestedPowerW);
  M5Dial.Display.setBrightness(SONNEN_ACTIVE_BRIGHTNESS);
  M5Dial.Display.setTextSize(1);
  M5Dial.Display.setTextDatum(middle_center);
  M5Dial.Encoder.write(0);
  lastEncoderPosition = M5Dial.Encoder.read();

  lastInteractionMs = millis();
  stateStartedMs = millis();
  drawUi();
  refreshStatus(true);
}

void loop() {
  M5Dial.update();
  handleEncoder();
  handleButton();
  maybeRefreshStatus();
  maintainPowerPolicy();
  delay(20);
}
