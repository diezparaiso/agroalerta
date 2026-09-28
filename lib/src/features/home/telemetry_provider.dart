import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../parcels/parcel_provider.dart';

class TelemetryWindow {
  const TelemetryWindow(this.hours);
  final int hours;

  String get label => hours == 24 ? '24 h' : '7 días';

  @override
  bool operator ==(Object other) => other is TelemetryWindow && other.hours == hours;

  @override
  int get hashCode => hours.hashCode;
}

final telemetryWindowProvider = StateProvider<TelemetryWindow>(
  (ref) => const TelemetryWindow(24),
);

final selectedTelemetryParcelIdProvider = StateProvider<String?>((ref) => null);
final selectedTelemetryDeviceIdProvider = StateProvider<String?>((ref) => null);

final telemetryHistoryProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final parcelId = ref.watch(selectedTelemetryParcelIdProvider);
  if (parcelId == null || parcelId.isEmpty) return const [];

  final window = ref.watch(telemetryWindowProvider);
  return ref.read(apiClientProvider).getTelemetry(
        parcelId,
        sinceHours: window.hours,
      );
});

final telemetryProvider = FutureProvider<Map<String, dynamic>?>((ref) async {
  final history = await ref.watch(telemetryHistoryProvider.future);
  return history.isEmpty ? null : history.first;
});

List<Map<String, dynamic>> telemetrySeries(
  List<Map<String, dynamic>> history,
  String field, {
  String? deviceId,
}) {
  final points = history
      .where((item) => (deviceId == null || item['device_id'] == deviceId) && item[field] is num && item['measured_at'] != null)
      .toList()
    ..sort(
      (a, b) => DateTime.parse(a['measured_at'] as String)
          .compareTo(DateTime.parse(b['measured_at'] as String)),
    );
  return points;
}
