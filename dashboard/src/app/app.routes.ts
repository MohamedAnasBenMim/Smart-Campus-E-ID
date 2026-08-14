import { Routes } from '@angular/router';
import { authGuard } from './core/auth-guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/login/login').then((m) => m.Login) },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/shell/shell').then((m) => m.Shell),
    children: [
      { path: '', redirectTo: 'overview', pathMatch: 'full' },
      {
        path: 'overview',
        loadComponent: () => import('./features/overview/overview').then((m) => m.Overview),
      },
      {
        path: 'personnes',
        loadComponent: () => import('./features/personnes/personnes').then((m) => m.PersonnesPage),
      },
      {
        path: 'zones',
        loadComponent: () => import('./features/zones/zones').then((m) => m.ZonesPage),
      },
      {
        path: 'regles',
        loadComponent: () => import('./features/regles/regles').then((m) => m.ReglesPage),
      },
      {
        path: 'alertes',
        loadComponent: () => import('./features/alertes/alertes').then((m) => m.AlertesPage),
      },
      {
        path: 'historique',
        loadComponent: () => import('./features/historique/historique').then((m) => m.HistoriquePage),
      },
      // Toutes les pages du dashboard sont maintenant construites.
    ],
  },
  { path: '**', redirectTo: '' },
];