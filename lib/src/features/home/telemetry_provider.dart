import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final telemetryProvider = FutureProvider<Map<String, dynamic>?>((ref) async {
  try {
    final parcels = await ref.watch(parcelsProvider.future);
    final id = parcels.isEmpty ? null : parcels.first.id;
    if (id == null) return null;
    return await ref.read(apiClientProvider).getLatestTelemetry(id);
  } catch (_) {
    return null;
  }
});
