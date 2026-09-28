import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/theme/app_theme.dart';
import 'features/auth/auth_gate.dart';
import 'features/alerts/alerts_screen.dart';
import 'features/alerts/alert_detail_screen.dart';
import 'features/home/home_screen.dart';
import 'features/parcels/parcels_screen.dart';
import 'features/products/products_screen.dart';
import 'features/reports/report_screen.dart';
import 'features/devices/devices_screen.dart';
import 'features/settings/settings_screen.dart';
import 'features/operation_center/operation_center_screen.dart';
import 'features/campaigns/campaigns_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final firebaseAvailable = ref.watch(firebaseAvailableProvider);
  return GoRouter(
    initialLocation: '/home',
    routes: [
      ShellRoute(
        builder: (context, state, child) => AuthGate(firebaseAvailable: firebaseAvailable, child: AppShell(child: child)),
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
          GoRoute(path: '/parcels', builder: (_, __) => const ParcelsScreen()),
          GoRoute(path: '/alerts', builder: (_, __) => const AlertsScreen()),
          GoRoute(path: '/alerts/:disease', builder: (_, state) => AlertDetailScreen(disease: state.pathParameters['disease'] ?? 'riesgo', parcelId: state.uri.queryParameters['parcelId'])),
          GoRoute(path: '/products', builder: (_, __) => const ProductsScreen()),
          GoRoute(path: '/reports/new', builder: (_, __) => const ReportScreen()),
          GoRoute(path: '/devices/:parcelId', builder: (_, state) => DevicesScreen(parcelId: state.pathParameters['parcelId'] ?? '')),
          GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
          GoRoute(path: '/operation-center', builder: (_, __) => const OperationCenterScreen()),
          GoRoute(path: '/campaigns', builder: (_, __) => const CampaignsScreen()),
        ],
      ),
    ],
  );
});

final firebaseAvailableProvider = Provider<bool>((ref) => false);

class AgroAlertaApp extends ConsumerWidget {
  const AgroAlertaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'AgroAlerta Andalucia',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: ref.watch(appRouterProvider),
    );
  }
}

class AppShell extends StatelessWidget {
  const AppShell({required this.child, super.key});
  final Widget child;

  static const destinations = [
    (label: 'Resumen', icon: Icons.dashboard_outlined, path: '/home'),
    (label: 'Parcelas', icon: Icons.landscape_outlined, path: '/parcels'),
    (label: 'Avisos', icon: Icons.warning_amber_rounded, path: '/alerts'),
    (label: 'Productos', icon: Icons.inventory_2_outlined, path: '/products'),
    (label: 'Ajustes', icon: Icons.settings_outlined, path: '/settings'),
    (label: 'Explotación', icon: Icons.agriculture_outlined, path: '/operation-center'),
    (label: 'Campañas', icon: Icons.event_note_outlined, path: '/campaigns'),
  ];

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    final selected = destinations.indexWhere((item) => location.startsWith(item.path));
    final width = MediaQuery.sizeOf(context).width;
    final compact = width < 700;
    final rail = width >= 700;

    return Scaffold(
      body: SafeArea(
        child: Row(
          children: [
            if (rail)
              NavigationRail(
                selectedIndex: selected < 0 ? 0 : selected,
                onDestinationSelected: (index) => context.go(destinations[index].path),
                extended: width >= 1100,
                leading: const Padding(
                  padding: EdgeInsets.only(top: 16, bottom: 24),
                  child: Icon(Icons.eco, size: 32),
                ),
                destinations: [
                  for (final item in destinations)
                    NavigationRailDestination(icon: Icon(item.icon), label: Text(item.label)),
                ],
              ),
            Expanded(child: child),
          ],
        ),
      ),
      bottomNavigationBar: compact
          ? NavigationBar(
              selectedIndex: selected < 0 ? 0 : selected,
              onDestinationSelected: (index) => context.go(destinations[index].path),
              destinations: [
                for (final item in destinations.take(4))
                  NavigationDestination(icon: Icon(item.icon), label: item.label),
              ],
            )
          : null,
    );
  }
}
