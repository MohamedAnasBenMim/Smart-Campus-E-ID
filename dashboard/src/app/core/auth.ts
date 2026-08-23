import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { Router } from '@angular/router';

export interface LoginResponse {
  token: string;
  nom: string;
  prenom: string;
  role: string; // 'ADMIN' | 'SURVEILLANT'
}

const STORAGE_KEY = 'smartcampus_auth';
const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class Auth {
  constructor(
    private http: HttpClient,
    private router: Router,
  ) {}

  login(email: string, motDePasse: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${API_BASE}/auth/login`, { email, motDePasse }).pipe(
      tap((response) => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(response));
      }),
    );
  }

  logout(): void {
    localStorage.removeItem(STORAGE_KEY);
    this.router.navigate(['/login']);
  }

  getCurrentUser(): LoginResponse | null {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  getToken(): string | null {
    return this.getCurrentUser()?.token ?? null;
  }

  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  isAdmin(): boolean {
    return this.getCurrentUser()?.role === 'ADMIN';
  }


  motDePasseOublie(email: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${API_BASE}/auth/mot-de-passe-oublie`, { email });
  }

  reinitialiserMotDePasse(token: string, nouveauMotDePasse: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${API_BASE}/auth/reinitialiser-mot-de-passe`, {
      token,
      nouveauMotDePasse,
    });
  }
}