import '../../core/notifications/notification_service.dart';
import '../settings/preferences_store.dart';

class AlertMonitor {
  AlertMonitor({NotificationService? notifications}) : _notifications = notifications ?? NotificationService();

  final NotificationService _notifications;

  Future<void> notifyRelevantAlerts(List<RiskAlertNotification> alerts) async {
    if (!await PreferencesStore().notificationsEnabled()) return;
    for (final alert in alerts.where((item) => item.level.toLowerCase() == 'alto' || item.level.toLowerCase() == 'medio')) {
      await _notifications.showRiskAlert(disease: alert.title, parcel: alert.parcel, level: alert.level);
    }
  }
}

class RiskAlertNotification {
  const RiskAlertNotification({required this.disease, required this.parcel, required this.level});

  final String disease;
  final String parcel;
  final String level;
}
