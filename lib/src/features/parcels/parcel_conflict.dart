enum ParcelConflictChoice { keepLocal, useRemote, cancel }

class ParcelConflictSummary {
  const ParcelConflictSummary({
    required this.localLabel,
    required this.remoteLabel,
    required this.localCrop,
    required this.remoteCrop,
    required this.localComarca,
    required this.remoteComarca,
  });

  final String localLabel;
  final String remoteLabel;
  final String localCrop;
  final String remoteCrop;
  final String localComarca;
  final String remoteComarca;

  bool get hasDifferences =>
      localLabel != remoteLabel ||
      localCrop != remoteCrop ||
      localComarca != remoteComarca;
}
