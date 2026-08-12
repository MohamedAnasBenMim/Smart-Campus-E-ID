import { Injectable, signal } from '@angular/core';

const STORAGE_KEY = 'smartcampus_theme';

@Injectable({ providedIn: 'root' })
export class Theme {
  sombre = signal(this.lireDepuisStockage());

  constructor() {
    this.appliquer(this.sombre());
  }

  basculer(): void {
    const nouveau = !this.sombre();
    this.sombre.set(nouveau);
    this.appliquer(nouveau);
    localStorage.setItem(STORAGE_KEY, nouveau ? 'dark' : 'light');
  }

  private appliquer(sombre: boolean): void {
    document.documentElement.setAttribute('data-theme', sombre ? 'dark' : 'light');
  }

  private lireDepuisStockage(): boolean {
    return localStorage.getItem(STORAGE_KEY) === 'dark';
  }
}