import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Cours } from '../models';

const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class CoursService {
  constructor(private http: HttpClient) {}

  lister(): Observable<Cours[]> {
    return this.http.get<Cours[]>(`${API_BASE}/cours`);
  }

  creer(cours: Partial<Cours>): Observable<Cours> {
    return this.http.post<Cours>(`${API_BASE}/cours`, cours);
  }

  modifier(id: string, cours: Partial<Cours>): Observable<Cours> {
    return this.http.put<Cours>(`${API_BASE}/cours/${id}`, cours);
  }

  supprimer(id: string): Observable<void> {
    return this.http.delete<void>(`${API_BASE}/cours/${id}`);
  }
}