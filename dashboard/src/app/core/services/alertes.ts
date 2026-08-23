import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Alerte } from '../models';

const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class Alertes {
  constructor(private http: HttpClient) {}

  lister(): Observable<Alerte[]> {
    return this.http.get<Alerte[]>(`${API_BASE}/alertes`);
  }

  marquerTraitee(id: string, commentaireTraitement: string, statut: string = 'TRAITEE'): Observable<Alerte> {
    return this.http.patch<Alerte>(`${API_BASE}/alertes/${id}`, { statut, commentaireTraitement });
  }

  // ============================================================
  // Traitement spécialisé — exploite l'embedding conservé sur
  // certaines alertes pour améliorer la reconnaissance.
  // ============================================================

  confirmerIdentite(alerteId: string): Observable<{ statut: string }> {
    return this.http.post<{ statut: string }>(`${API_BASE}/alertes/${alerteId}/confirmer-identite`, {});
  }

  corrigerIdentite(alerteId: string, vraiePersonneId?: string): Observable<{ statut: string }> {
    return this.http.post<{ statut: string }>(`${API_BASE}/alertes/${alerteId}/corriger-identite`, {
      vraiePersonneId: vraiePersonneId ?? null,
    });
  }

  associerPersonne(alerteId: string, personneId: string): Observable<{ statut: string }> {
    return this.http.post<{ statut: string }>(`${API_BASE}/alertes/${alerteId}/associer-personne`, { personneId });
  }

  enrolerDepuisAlerte(
    alerteId: string,
    nom: string,
    prenom: string | null,
    role: string,
  ): Observable<{ id: string; nom: string }> {
    return this.http.post<{ id: string; nom: string }>(`${API_BASE}/alertes/${alerteId}/enroler`, {
      nom,
      prenom,
      role,
    });
  }
}