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

  marquerTraitee(id: string, statut: string = 'TRAITEE'): Observable<Alerte> {
    return this.http.patch<Alerte>(`${API_BASE}/alertes/${id}`, { statut });
  }
}