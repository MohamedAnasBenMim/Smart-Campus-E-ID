import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Personne } from '../models';

const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class Personnes {
  constructor(private http: HttpClient) {}

  lister(): Observable<Personne[]> {
    return this.http.get<Personne[]>(`${API_BASE}/personnes`);
  }

  consulter(id: string): Observable<Personne> {
    return this.http.get<Personne>(`${API_BASE}/personnes/${id}`);
  }

  creer(formData: FormData): Observable<Personne> {
    // multipart (nom, prenom, email, telephone, role, images[]) — voir PersonneController
    return this.http.post<Personne>(`${API_BASE}/personnes`, formData);
  }

  modifier(id: string, modifications: Partial<Personne>): Observable<Personne> {
    return this.http.put<Personne>(`${API_BASE}/personnes/${id}`, modifications);
  }

  supprimer(id: string): Observable<void> {
    return this.http.delete<void>(`${API_BASE}/personnes/${id}`);
  }
}