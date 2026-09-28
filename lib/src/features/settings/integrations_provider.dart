import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final integrationsHealthProvider = FutureProvider<Map<String, dynamic>>((ref) => ref.read(apiClientProvider).getIntegrationsHealth());
