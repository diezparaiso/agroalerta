import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  final plugin = FlutterLocalNotificationsPlugin();

  Future<void> initialize() async {
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    const settings = InitializationSettings(android: android, iOS: DarwinInitializationSettings());
    await plugin.initialize(settings);
    await plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()?.requestNotificationsPermission();
    await plugin.resolvePlatformSpecificImplementation<IOSFlutterLocalNotificationsPlugin>()?.requestPermissions(alert: true, badge: true, sound: true);
  }

  Future<void> showRiskAlert({required String disease, required String parcel, required String level}) async {
    const details = NotificationDetails(
      android: AndroidNotificationDetails('agroalerta-risk', 'Avisos de riesgo', channelDescription: 'Avisos fitosanitarios de tus parcelas', importance: Importance.high, priority: Priority.high),
      iOS: DarwinNotificationDetails(),
    );
    await plugin.show(disease.hashCode, 'Riesgo $level: $disease', parcel, details);
  }
}
