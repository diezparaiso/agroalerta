import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../parcels/parcel_provider.dart';

final selectedCampaignParcelProvider = StateProvider<String?>((ref) => null);

final campaignsProvider = FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final parcelId = ref.watch(selectedCampaignParcelProvider);
  if (parcelId == null) return const [];
  return ref.watch(apiClientProvider).getCampaigns(parcelId);
});
