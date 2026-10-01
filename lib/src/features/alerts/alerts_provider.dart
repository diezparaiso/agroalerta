import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';
import 'alert_monitor.dart';

final alertsProvider = FutureProvider<List<AlertSummary>>((ref) async {
  try {
    final records = await ref.read(apiClientProvider).getAlerts();
    final alerts = records.map(AlertSummary.fromJson).toList();
    await AlertMonitor().notifyRelevantAlerts([for (final alert in alerts) RiskAlertNotification(disease: alert.title, parcel: alert.parcel, level: alert.level)]);
    return alerts;
  } catch (_) {
    rethrow;
  }
});

class AlertSummary {
  const AlertSummary({required this.title, required this.parcel, required this.level, required this.value, required this.dataStatus});

  final String title;
  final String parcel;
  final String level;
  final double value;
  final String dataStatus;

  factory AlertSummary.fromJson(Map<String, dynamic> json) => AlertSummary(
        title: json['disease_code'] as String? ?? 'Riesgo',
        parcel: json['parcel_id'] as String? ?? 'Parcela',
        level: json['risk_level'] as String? ?? 'Bajo',
        value: (json['risk_score'] as num?)?.toDouble() ?? 0,
        dataStatus: json['data_status'] as String? ?? 'insuficiente',
      );
}
