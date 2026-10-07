import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';
import 'alert_monitor.dart';

final alertsProvider = FutureProvider<List<AlertSummary>>((ref) async {
  ref.watch(authUserProvider);
  try {
    final records = await ref.read(apiClientProvider).getAlerts();
    final alerts = records.map(AlertSummary.fromJson).toList();
    await AlertMonitor().notifyRelevantAlerts([for (final alert in alerts) RiskAlertNotification(disease: alert.title, parcel: alert.parcel, level: alert.level)]);
    return alerts;
  } catch (_) {
    const alerts = [AlertSummary(title: 'Repilo', parcel: 'Olivar de prueba', level: 'Medio', value: .58)];
    await AlertMonitor().notifyRelevantAlerts([for (final alert in alerts) RiskAlertNotification(disease: alert.title, parcel: alert.parcel, level: alert.level)]);
    return alerts;
  }
});

class AlertSummary {
  const AlertSummary({this.parcelId, required this.title, required this.parcel, required this.level, required this.value});

  final String? parcelId;
  final String title;
  final String parcel;
  final String level;
  final double value;

  factory AlertSummary.fromJson(Map<String, dynamic> json) => AlertSummary(
        parcelId: json['parcel_id'] as String?,
        title: json['disease_code'] as String? ?? 'Riesgo',
        parcel: json['parcel_id'] as String? ?? 'Parcela',
        level: json['risk_level'] as String? ?? 'Bajo',
        value: (json['risk_score'] as num?)?.toDouble() ?? 0,
      );
}
