import 'package:firebase_messaging/firebase_messaging.dart';

import '../network/api_client.dart';

class PushTokenService {
  PushTokenService({ApiClient? apiClient}) : _apiClient = apiClient ?? ApiClient();

  final ApiClient _apiClient;

  Future<void> register() async {
    final messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(alert: true, badge: true, sound: true);
    final token = await messaging.getToken();
    if (token != null) await _apiClient.registerPushToken(token);
    messaging.onTokenRefresh.listen(_apiClient.registerPushToken);
  }

  Future<void> unregister() async {
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null) await _apiClient.unregisterPushToken(token);
    await FirebaseMessaging.instance.deleteToken();
  }
}
