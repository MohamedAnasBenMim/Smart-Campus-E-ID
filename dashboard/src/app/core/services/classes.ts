import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Classe } from '../models';

const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class ClassesService {
  constructor(private http: HttpClient) {}

  lister(): Observable<Classe[]> {
    return this.http.get<Classe[]>(`${API_BASE}/classes`);
  }

  creer(classe: Partial<Classe>): Observable<Classe> {
    return this.http.post<Classe>(`${API_BASE}/classes`, classe);
  }

  supprimer(id: string): Observable<void> {
    return this.http.delete<void>(`${API_BASE}/classes/${id}`);
  }
}