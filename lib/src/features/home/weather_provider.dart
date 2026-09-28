import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final weatherProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final parcels = await ref.watch(parcelsProvider.future);
  final id = parcels.isEmpty ? null : parcels.first.id;
  if (id == null) return const <String, dynamic>{'source': 'none', 'confidence': 'no_disponible'};

  try {
    return await ref.read(apiClientProvider).getWeather(id);
  } catch (_) {
    return const <String, dynamic>{'source': 'none', 'confidence': 'no_disponible'};
  }
});

String weatherDisplayValue(Map<String, dynamic> weather, String key) {
  final value = weather[key];
  return value == null ? 'No disponible' : value.toString();
}
