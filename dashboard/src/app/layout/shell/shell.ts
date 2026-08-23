import { Component, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatBadgeModule } from '@angular/material/badge';
import { Auth } from '../../core/auth';
import { Theme } from '../../core/theme';
import { Alertes } from '../../core/services/alertes';

interface MenuItem {
  label: string;
  icon: string;
  route: string;
  rolesAutorises: string[]; // ADMIN, SURVEILLANT
}

const MENU_ITEMS: MenuItem[] = [
  { label: "Vue d'ensemble", icon: 'dashboard', route: '/overview', rolesAutorises: ['ADMIN', 'SURVEILLANT'] },
  { label: 'Personnes', icon: 'people', route: '/personnes', rolesAutorises: ['ADMIN'] },
  { label: 'Cours', icon: 'menu_book', route: '/cours', rolesAutorises: ['ADMIN'] },
  { label: 'Classes', icon: 'groups', route: '/classes', rolesAutorises: ['ADMIN'] },
  { label: 'Emploi du temps', icon: 'calendar_view_week', route: '/emploi-du-temps', rolesAutorises: ['ADMIN', 'SURVEILLANT'] },
  { label: 'Historique présence', icon: 'fact_check', route: '/historique-appels', rolesAutorises: ['ADMIN', 'SURVEILLANT'] },
  { label: 'Zones', icon: 'place', route: '/zones', rolesAutorises: ['ADMIN'] },
  { label: 'Règles par rôle', icon: 'admin_panel_settings', route: '/regles-role', rolesAutorises: ['ADMIN'] },
  { label: "Règles d'accès", icon: 'rule', route: '/regles', rolesAutorises: ['ADMIN'] },
  { label: 'Alertes', icon: 'notifications_active', route: '/alertes', rolesAutorises: ['ADMIN', 'SURVEILLANT'] },
  {
    label: 'Evenements accès',
    icon: 'history',
    route: '/historique',
    rolesAutorises: ['ADMIN', 'SURVEILLANT'],
  },
];

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatSidenavModule,
    MatToolbarModule,
    MatListModule,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatBadgeModule,
  ],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell implements OnInit, OnDestroy {
  now = signal(new Date());
  alertesNonTraitees = signal(0);

  formattedTime = computed(() => this.now().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }));

  private clockInterval?: ReturnType<typeof setInterval>;
  private alertesInterval?: ReturnType<typeof setInterval>;

  constructor(
    public auth: Auth,
    public theme: Theme,
    private alertesService: Alertes,
  ) {}

  ngOnInit(): void {
    this.clockInterval = setInterval(() => this.now.set(new Date()), 30_000);
    this.rafraichirAlertes();
    this.alertesInterval = setInterval(() => this.rafraichirAlertes(), 15_000);
  }

  ngOnDestroy(): void {
    if (this.clockInterval) clearInterval(this.clockInterval);
    if (this.alertesInterval) clearInterval(this.alertesInterval);
  }

  get menuVisible(): MenuItem[] {
    const role = this.auth.getCurrentUser()?.role ?? '';
    return MENU_ITEMS.filter((item) => item.rolesAutorises.includes(role));
  }

  get initiales(): string {
    const user = this.auth.getCurrentUser();
    if (!user) return '?';
    return `${user.prenom?.[0] ?? ''}${user.nom?.[0] ?? ''}`.toUpperCase();
  }

  private rafraichirAlertes(): void {
    this.alertesService.lister().subscribe({
      next: (alertes) => {
        this.alertesNonTraitees.set(alertes.filter((a) => a.statut === 'NON_TRAITEE').length);
      },
      error: () => {
        // silencieux : le badge reste juste à sa dernière valeur connue
      },
    });
  }
}