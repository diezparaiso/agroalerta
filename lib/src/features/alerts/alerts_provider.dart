import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';
import 'alert_monitor.dart';

final alertsProvider = FutureProvider<List<AlertSummary>>((ref) async {
  try {
    final records = await ref.read(apiClientProvider).getAlerts();
    final alerts = records.map(AlertSummary.fromJson).toList();
    await AlertMonitor().notifyRelevantAlerts([
      for (final alert in alerts)
        RiskAlertNotification(disease: alert.title, parcel: alert.parcel, level: alert.level),
    ]);
    return alerts;
  } catch (_) {
    const alerts = [
      AlertSummary(title: 'Repilo', parcelId: null, parcel: 'Olivar de prueba', level: 'Medio', value: .58),
    ];
    await AlertMonitor().notifyRelevantAlerts([
      for (final alert in alerts)
        RiskAlertNotification(disease: alert.title, parcel: alert.parcel, level: alert.level),
    ]);
    return alerts;
  }
});

class AlertSummary {
  const AlertSummary({
    required this.title,
    required this.parcelId,
    required this.parcel,
    required this.level,
    required this.value,
  });

  final String title;
  final String? parcelId;
  final String parcel;
  final String level;
  final double value;

  factory AlertSummary.fromJson(Map<String, dynamic> json) => AlertSummary(
        title: json['disease_code'] as String? ?? 'Riesgo',
        parcelId: json['parcel_id'] as String?,
        parcel: json['parcel_label'] as String? ?? json['parcel_id'] as String? ?? 'Parcela',
        level: json['risk_level'] as String? ?? 'bajo',
        value: (json['risk_score'] as num?)?.toDouble() ?? 0,
      );
}
