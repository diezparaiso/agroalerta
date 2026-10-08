import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../alerts/alerts_provider.dart';
import '../parcels/parcel_provider.dart';
import 'weather_provider.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = FirebaseAuth.instance.currentUser;
    final name = user?.displayName?.trim().split(RegExp(r'\s+')).first;
    final firstName = (name == null || name.isEmpty) ? 'agricultor' : name;

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Theme.of(context).colorScheme.surface,
            Theme.of(context).colorScheme.surfaceContainerLowest,
          ],
        ),
      ),
      child: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(weatherProvider);
          ref.invalidate(alertsProvider);
          ref.invalidate(parcelsProvider);
          await Future<void>.delayed(const Duration(milliseconds: 250));
        },
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(child: _HeroHeader(firstName: firstName)),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  _WeatherCard(ref: ref),
                  const SizedBox(height: 16),
                  _AlertsBanner(ref: ref),
                  const SizedBox(height: 20),
                  const _QuickActions(),
                  const SizedBox(height: 28),
                  _SectionHeader(
                    title: 'Mis parcelas',
                    onAction: () => context.go('/parcels'),
                  ),
                  const SizedBox(height: 12),
                  _Parcels(ref: ref),
                  const SizedBox(height: 20),
                  const _InsightCard(
                    icon: Icons.water_drop_outlined,
                    title: 'Inteligencia hídrica',
                    text: 'Consulta las recomendaciones de riego de tus parcelas.',
                    route: '/irrigation',
                  ),
                  const SizedBox(height: 12),
                  const _InsightCard(
                    icon: Icons.sensors_outlined,
                    title: 'Sensores e IoT',
                    text: 'Consulta telemetría y estado de tus dispositivos.',
                    route: '/operation-center',
                  ),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HeroHeader extends StatelessWidget {
  const _HeroHeader({required this.firstName});
  final String firstName;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.fromLTRB(24, 32, 24, 28),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            scheme.primary,
            Color.lerp(scheme.primary, scheme.tertiary, .45) ?? scheme.primary,
          ],
        ),
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(30)),
        boxShadow: [
          BoxShadow(
            color: scheme.primary.withValues(alpha: .18),
            blurRadius: 22,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: .92),
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.eco, color: scheme.primary, size: 30),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Text(
                  'AgroAlerta',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 27,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              IconButton(
                onPressed: () => context.go('/settings'),
                style: IconButton.styleFrom(
                  backgroundColor: Colors.white.withValues(alpha: .16),
                  foregroundColor: Colors.white,
                ),
                icon: const Icon(Icons.person_outline),
              ),
            ]),
            const SizedBox(height: 26),
            Text(
              'Hola, ' + firstName,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 29,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 5),
            Text(
              'Estas son las novedades de tus parcelas',
              style: TextStyle(
                color: Colors.white.withValues(alpha: .88),
                fontSize: 15,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WeatherCard extends StatelessWidget {
  const _WeatherCard({required this.ref});
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      elevation: 2,
      shadowColor: scheme.shadow.withValues(alpha: .12),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: ref.watch(weatherProvider).when(
          data: (weather) {
            final temperature = weather['temperature_c'];
            final humidity = weather['relative_humidity'];
            final rain = weather['rainfall_mm_24h'];
            final source = weather['source'] == 'ria-ifapa' ? 'RIA / IFAPA' : 'AEMET';
            return Row(
              children: [
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    color: scheme.primaryContainer,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Icon(Icons.wb_cloudy_outlined, size: 38, color: scheme.primary),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        temperature == null ? '-- °C' : temperature.toString() + ' °C',
                        style: const TextStyle(fontSize: 30, fontWeight: FontWeight.w800),
                      ),
                      Text('Condiciones actuales · ' + source),
                    ],
                  ),
                ),
                if (MediaQuery.sizeOf(context).width >= 430)
                  _Metric(
                    icon: Icons.water_drop_outlined,
                    label: 'Humedad',
                    value: humidity == null ? '--' : humidity.toString() + '%',
                  ),
                if (MediaQuery.sizeOf(context).width >= 520) ...[
                  const SizedBox(width: 18),
                  _Metric(
                    icon: Icons.umbrella_outlined,
                    label: 'Lluvia',
                    value: rain == null ? '--' : rain.toString() + ' mm',
                  ),
                ],
              ],
            );
          },
          loading: () => const _LoadingRow(text: 'Consultando clima real...'),
          error: (_, __) => Row(children: [
            Icon(Icons.cloud_off_outlined, color: scheme.error),
            const SizedBox(width: 12),
            const Expanded(child: Text('Clima no disponible en este momento.')),
            IconButton(
              onPressed: () => ref.invalidate(weatherProvider),
              icon: const Icon(Icons.refresh),
            ),
          ]),
        ),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.icon, required this.label, required this.value});
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Icon(icon, size: 18, color: Theme.of(context).colorScheme.primary),
      const SizedBox(height: 4),
      Text(label, style: Theme.of(context).textTheme.labelMedium),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
    ],
  );
}

class _AlertsBanner extends StatelessWidget {
  const _AlertsBanner({required this.ref});
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ref.watch(alertsProvider).when(
      data: (alerts) {
        final high = alerts.where((a) => a.level.toLowerCase() == 'alto').length;
        final medium = alerts.where((a) => a.level.toLowerCase() == 'medio').length;
        final count = alerts.length;
        final detail = [
          if (high > 0) high.toString() + ' de riesgo alto',
          if (medium > 0) medium.toString() + ' de riesgo medio',
        ].join(' · ');
        return _Banner(
          icon: count == 0 ? Icons.verified_outlined : Icons.notifications_active_outlined,
          title: count == 0 ? 'Sin alertas activas' : count.toString() + (count == 1 ? ' alerta activa' : ' alertas activas'),
          subtitle: count == 0 ? 'No hay avisos de riesgo para tus parcelas.' : (detail.isEmpty ? 'Revisa los avisos de tus parcelas.' : detail),
          background: count == 0
              ? scheme.primaryContainer.withValues(alpha: .55)
              : scheme.errorContainer.withValues(alpha: .55),
          foreground: count == 0 ? scheme.primary : scheme.error,
          onTap: () => context.go('/alerts'),
        );
      },
      loading: () => const _LoadingRow(text: 'Comprobando alertas...'),
      error: (_, __) => _Banner(
        icon: Icons.notifications_none,
        title: 'Avisos no disponibles',
        subtitle: 'Pulsa para abrir el centro de alertas.',
        background: scheme.surfaceContainerHighest,
        foreground: scheme.onSurfaceVariant,
        onTap: () => context.go('/alerts'),
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.background,
    required this.foreground,
    required this.onTap,
  });
  final IconData icon;
  final String title;
  final String subtitle;
  final Color background;
  final Color foreground;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
    color: background,
    child: InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        child: Row(children: [
          CircleAvatar(
            backgroundColor: foreground.withValues(alpha: .14),
            foregroundColor: foreground,
            child: Icon(icon),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: foreground)),
                const SizedBox(height: 3),
                Text(subtitle),
              ],
            ),
          ),
          const Icon(Icons.chevron_right),
        ]),
      ),
    ),
  );
}

class _QuickActions extends StatelessWidget {
  const _QuickActions();

  @override
  Widget build(BuildContext context) {
    final actions = [
      _Action('Mis parcelas', 'Ver y gestionar', Icons.landscape_outlined, const Color(0xFF2E7D32), '/parcels'),
      _Action('Meteorología', 'RIA / AEMET', Icons.cloud_outlined, const Color(0xFF1976D2), '/home'),
      _Action('Alertas', 'Riesgos y avisos', Icons.warning_amber_rounded, const Color(0xFFE68A00), '/alerts'),
      _Action('Actividad', 'Historial de campo', Icons.timeline_outlined, const Color(0xFF5E35B1), '/timeline'),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 760 ? 4 : 2;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: actions.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: columns == 4 ? 1.5 : 1.65,
          ),
          itemBuilder: (_, index) => actions[index],
        );
      },
    );
  }
}

class _Action extends StatelessWidget {
  const _Action(this.label, this.hint, this.icon, this.color, this.route);
  final String label;
  final String hint;
  final IconData icon;
  final Color color;
  final String route;

  @override
  Widget build(BuildContext context) => Card(
    child: InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: () => context.go(route),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: color.withValues(alpha: .12),
              foregroundColor: color,
              child: Icon(icon, size: 27),
            ),
            const SizedBox(height: 9),
            Text(label, style: const TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 2),
            Text(hint, style: Theme.of(context).textTheme.bodySmall, textAlign: TextAlign.center),
          ],
        ),
      ),
    ),
  );
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, required this.onAction});
  final String title;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) => Row(children: [
    Expanded(child: Text(title, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800))),
    TextButton.icon(
      onPressed: onAction,
      icon: const Icon(Icons.arrow_forward, size: 17),
      label: const Text('Ver todas'),
      iconAlignment: IconAlignment.end,
    ),
  ]);
}

class _Parcels extends StatelessWidget {
  const _Parcels({required this.ref});
  final WidgetRef ref;

  @override
  Widget build(BuildContext context) => ref.watch(parcelsProvider).when(
    data: (parcels) {
      if (parcels.isEmpty) {
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(22),
            child: Row(children: [
              CircleAvatar(
                backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                child: Icon(Icons.add_location_alt_outlined, color: Theme.of(context).colorScheme.primary),
              ),
              const SizedBox(width: 14),
              const Expanded(child: Text('Todavía no tienes parcelas. Añade una para empezar a recibir avisos personalizados.')),
              FilledButton(onPressed: () => context.go('/parcels'), child: const Text('Añadir')),
            ]),
          ),
        );
      }
      return Column(
        children: [
          for (final parcel in parcels.take(4)) ...[
            _ParcelTile(parcel: parcel),
            const SizedBox(height: 10),
          ],
        ],
      );
    },
    loading: () => const _LoadingRow(text: 'Cargando parcelas...'),
    error: (_, __) => const _EmptyState(icon: Icons.landscape_outlined, text: 'No se han podido cargar las parcelas.'),
  );
}

class _ParcelTile extends StatelessWidget {
  const _ParcelTile({required this.parcel});
  final ParcelSummary parcel;

  @override
  Widget build(BuildContext context) {
    final level = parcel.risk.toLowerCase();
    final color = level == 'alto'
        ? Theme.of(context).colorScheme.error
        : level == 'medio'
            ? const Color(0xFFE68A00)
            : Theme.of(context).colorScheme.primary;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => context.go('/parcels'),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(children: [
            Container(
              width: 72,
              height: 62,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                color: Theme.of(context).colorScheme.primaryContainer,
              ),
              child: Icon(
                parcel.crop.toLowerCase().contains('oliv') ? Icons.park_outlined : Icons.agriculture_outlined,
                color: Theme.of(context).colorScheme.primary,
                size: 30,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(parcel.name, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 3),
                  Text(parcel.place + ' · ' + parcel.crop),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Container(
              constraints: const BoxConstraints(minWidth: 74),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: color.withValues(alpha: .11),
                borderRadius: BorderRadius.circular(11),
              ),
              child: Column(children: [
                Icon(Icons.shield_outlined, color: color, size: 18),
                const SizedBox(height: 2),
                Text(parcel.risk, style: TextStyle(color: color, fontWeight: FontWeight.w800, fontSize: 12)),
              ]),
            ),
            const Icon(Icons.chevron_right),
          ]),
        ),
      ),
    );
  }
}

class _InsightCard extends StatelessWidget {
  const _InsightCard({
    required this.icon,
    required this.title,
    required this.text,
    required this.route,
  });
  final IconData icon;
  final String title;
  final String text;
  final String route;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      color: scheme.primaryContainer.withValues(alpha: .30),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => context.go(route),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(children: [
            CircleAvatar(
              backgroundColor: scheme.primary.withValues(alpha: .12),
              foregroundColor: scheme.primary,
              child: Icon(icon),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 3),
                  Text(text),
                ],
              ),
            ),
            const Icon(Icons.chevron_right),
          ]),
        ),
      ),
    );
  }
}

class _LoadingRow extends StatelessWidget {
  const _LoadingRow({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Row(children: [
        const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2)),
        const SizedBox(width: 14),
        Text(text),
      ]),
    ),
  );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.icon, required this.text});
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(20),
      child: Row(children: [
        Icon(icon, size: 28),
        const SizedBox(width: 12),
        Expanded(child: Text(text)),
      ]),
    ),
  );
}
