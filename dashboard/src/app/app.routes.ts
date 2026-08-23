import { Routes } from '@angular/router';
import { authGuard } from './core/auth-guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/login/login').then((m) => m.Login) },
  {
    path: 'mot-de-passe-oublie',
    loadComponent: () => import('./features/mot-de-passe-oublie/mot-de-passe-oublie').then((m) => m.MotDePasseOubliePage),
  },
  {
    path: 'reinitialiser-mot-de-passe',
    loadComponent: () => import('./features/reinitialiser-mot-de-passe/reinitialiser-mot-de-passe').then((m) => m.ReinitialiserMotDePassePage),
  },
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
        path: 'cours',
        loadComponent: () => import('./features/cours/cours').then((m) => m.CoursPage),
      },
      {
        path: 'classes',
        loadComponent: () => import('./features/classes/classes').then((m) => m.ClassesPage),
      },
      {
        path: 'emploi-du-temps',
        loadComponent: () => import('./features/emploi-du-temps/emploi-du-temps').then((m) => m.EmploiDuTempsPage),
      },
      {
        path: 'alertes',
        loadComponent: () => import('./features/alertes/alertes').then((m) => m.AlertesPage),
      },
      {
        path: 'historique',
        loadComponent: () => import('./features/historique/historique').then((m) => m.HistoriquePage),
      },
      {
        path: 'historique-appels',
        loadComponent: () => import('./features/historique-appels/historique-appels').then((m) => m.HistoriqueAppelsPage),
      },
      {
        path: 'regles-role',
        loadComponent: () => import('./features/regles-role/regles-role').then((m) => m.ReglesRolePage),
      },

      // Toutes les pages du dashboard sont maintenant construites.
    ],
  },
  { path: '**', redirectTo: '' },
];