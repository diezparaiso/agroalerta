import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../home/home_screen.dart';
import 'preferences_store.dart';
import '../../core/ads/ad_consent_store.dart';
import '../../core/privacy/local_data_manager.dart';
import '../../core/notifications/push_token_service.dart';
import 'integrations_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final store = PreferencesStore();
  bool notifications = true;
  bool offline = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final values = await Future.wait([store.notificationsEnabled(), store.offlineCacheEnabled()]);
    if (mounted) setState(() { notifications = values[0]; offline = values[1]; });
  }

  @override
  Widget build(BuildContext context) { final user = FirebaseAuth.instance.currentUser; return AppPage(title: 'Ajustes', subtitle: 'Preferencias y privacidad', child: ListView(children: [Card(child: ListTile(leading: const CircleAvatar(child: Icon(Icons.person_outline)), title: Text(user?.email ?? 'Cuenta autenticada'), subtitle: Text('ID: ${user?.uid ?? 'local'}'))), Card(child: Column(children: [SwitchListTile(secondary: const Icon(Icons.notifications_outlined), title: const Text('Avisos de severidad media o alta'), value: notifications, onChanged: (value) { setState(() => notifications = value); store.setNotificationsEnabled(value); }), SwitchListTile(secondary: const Icon(Icons.wifi_off_outlined), title: const Text('Mostrar datos en cache'), value: offline, onChanged: (value) { setState(() => offline = value); store.setOfflineCacheEnabled(value); })])), Card(child: Column(children: [const ListTile(leading: Icon(Icons.cloud_outlined), title: Text('Estado de integraciones')), ref.watch(integrationsHealthProvider).when(data: (health) => [for (final entry in health.entries) ListTile(dense: true, leading: Icon(Icons.circle, size: 12, color: (entry.value as Map<String, dynamic>)['configured'] == true ? Colors.green : Colors.orange), title: Text(entry.key), subtitle: Text((entry.value as Map<String, dynamic>)['mode'] as String? ?? 'desconocido')], loading: () => const [ListTile(title: Text('Consultando...'))], error: (_, __) => const [ListTile(title: Text('Estado no disponible'))])])), Card(child: ListTile(leading: const Icon(Icons.privacy_tip_outlined), title: const Text('Revocar consentimiento publicitario'), onTap: () async { await AdConsentStore().revokeConsent(); if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Consentimiento publicitario revocado'))); })), Card(child: ListTile(leading: const Icon(Icons.delete_outline), title: const Text('Eliminar datos del dispositivo'), onTap: () => _deleteLocalData(context))), const Card(child: ListTile(leading: Icon(Icons.privacy_tip_outlined), title: Text('Privacidad y datos de parcelas'), trailing: Icon(Icons.chevron_right))), Card(child: ListTile(leading: const Icon(Icons.logout), title: const Text('Cerrar sesion'), onTap: () async { try { await PushTokenService().unregister(); } catch (_) {} await FirebaseAuth.instance.signOut(); }))])); }

  Future<void> _deleteLocalData(BuildContext context) async {
    final confirmed = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(title: const Text('Eliminar datos locales'), content: const Text('Se borraran las parcelas, reportes pendientes y preferencias de este dispositivo.'), actions: [TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancelar')), FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Eliminar'))])) ?? false;
    if (!confirmed) return;
    final userId = FirebaseAuth.instance.currentUser?.uid ?? 'offline-user';
    await LocalDataManager().deleteUserData(userId);
    if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Datos locales eliminados')));
  }
}
