import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final operationCenterProvider = FutureProvider<Map<String, dynamic>>((ref) {
  return ref.watch(apiClientProvider).getFarmCenter();
});
