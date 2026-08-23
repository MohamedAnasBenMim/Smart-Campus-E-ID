import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RegleAcces } from '../models';

const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class Regles {
  constructor(private http: HttpClient) {}

  lister(): Observable<RegleAcces[]> {
    return this.http.get<RegleAcces[]>(`${API_BASE}/regles`);
  }

  creer(regle: {
    personneId: string;
    zoneId: string;
    horaireDebut: string;
    horaireFin: string;
  }): Observable<RegleAcces> {
    return this.http.post<RegleAcces>(`${API_BASE}/regles`, regle);
  }

  modifier(
    id: string,
    regle: { personneId: string; zoneId: string; horaireDebut: string; horaireFin: string },
  ): Observable<RegleAcces> {
    return this.http.put<RegleAcces>(`${API_BASE}/regles/${id}`, regle);
  }

  supprimer(id: string): Observable<void> {
    return this.http.delete<void>(`${API_BASE}/regles/${id}`);
  }
}