import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RegleAccesRole } from '../models/regle-role';

const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class ReglesRoleService {
  constructor(private http: HttpClient) {}

  lister(): Observable<RegleAccesRole[]> {
    return this.http.get<RegleAccesRole[]>(`${API_BASE}/regles-role`);
  }

  creer(regle: Partial<RegleAccesRole>): Observable<RegleAccesRole> {
    return this.http.post<RegleAccesRole>(`${API_BASE}/regles-role`, regle);
  }

  /**
   * NOUVEAU — création groupée : un rôle, plusieurs zones d'un coup,
   * un seul horaire pour toutes.
   */
  creerEnLot(lot: {
    role: string;
    zoneIds: string[];
    horaireDebut: string;
    horaireFin: string;
  }): Observable<RegleAccesRole[]> {
    return this.http.post<RegleAccesRole[]>(`${API_BASE}/regles-role/lot`, lot);
  }

  modifier(id: string, regle: Partial<RegleAccesRole>): Observable<RegleAccesRole> {
    return this.http.put<RegleAccesRole>(`${API_BASE}/regles-role/${id}`, regle);
  }

  supprimer(id: string): Observable<void> {
    return this.http.delete<void>(`${API_BASE}/regles-role/${id}`);
  }
}