import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Zone } from '../models';

const API_BASE = 'http://localhost:8080/api';

@Injectable({ providedIn: 'root' })
export class Zones {
  constructor(private http: HttpClient) {}

  lister(): Observable<Zone[]> {
    return this.http.get<Zone[]>(`${API_BASE}/zones`);
  }

  creer(zone: Partial<Zone>): Observable<Zone> {
    return this.http.post<Zone>(`${API_BASE}/zones`, zone);
  }

  supprimer(id: string): Observable<void> {
    return this.http.delete<void>(`${API_BASE}/zones/${id}`);
  }
}