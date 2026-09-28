import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'src/app.dart';
import 'src/core/ads/ads_service.dart';
import 'src/core/notifications/notification_service.dart';
import 'src/features/reports/offline_sync_service.dart';
import 'src/core/notifications/push_token_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  var firebaseAvailable = true;
  try {
    await Firebase.initializeApp();
  } catch (_) {
    firebaseAvailable = false;
  }
  try {
    await initializeAds();
  } catch (_) {}
  final notificationService = NotificationService();
  try {
    await notificationService.initialize();
  } catch (_) {}
  if (firebaseAvailable) {
    FirebaseMessaging.onMessage.listen((message) {
      final data = message.data;
      final disease = data['disease_code']?.toString();
      final parcel = data['parcel_id']?.toString();
      final level = data['risk_level']?.toString();
      if (disease == null || parcel == null || level == null) return;
      notificationService.showRiskAlert(
        disease: disease,
        parcel: parcel,
        level: level,
      );
    });
  }
  if (firebaseAvailable) {
    try {
      await PushTokenService().register();
    } catch (_) {}
  }
  try {
    OfflineSyncService().start();
  } catch (_) {}
  runApp(ProviderScope(overrides: [firebaseAvailableProvider.overrideWithValue(firebaseAvailable)], child: const AgroAlertaApp()));
}
