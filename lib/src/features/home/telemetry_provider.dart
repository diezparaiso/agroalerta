import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../parcels/parcel_provider.dart';

class TelemetryWindow {
  const TelemetryWindow(this.hours);
  final int hours;

  String get label => hours == 24 ? '24 h' : '7 días';
}

final telemetryWindowProvider = StateProvider<TelemetryWindow>(
  (ref) => const TelemetryWindow(24),
);

final telemetryHistoryProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final parcels = await ref.watch(parcelsProvider.future);
  final parcelId = parcels.isEmpty ? null : parcels.first.id;
  if (parcelId == null) return const [];

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
  String field,
) {
  final points = history
      .where((item) => item[field] is num && item['measured_at'] != null)
      .toList()
    ..sort(
      (a, b) => DateTime.parse(a['measured_at'] as String)
          .compareTo(DateTime.parse(b['measured_at'] as String)),
    );
  return points;
}
