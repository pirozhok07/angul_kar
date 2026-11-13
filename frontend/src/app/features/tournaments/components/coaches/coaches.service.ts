import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { Club } from '../clubs/clubs.service';

export interface Coach {
  id: number;
  [key: string]: unknown;
}

export interface CoachesField {
  name: string;
  type: string;
  nullable: boolean;
  required: boolean;
}

@Injectable({
    providedIn: 'root'
})
export class CoachesService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments';

  private url(tournamentId: number): string {
    return `${this.apiUrl}/${tournamentId}/coaches`;
  }

  getFields(tournamentId: number): Observable<CoachesField[]> {
    return this.http.get<CoachesField[]>(`${this.url(tournamentId)}/fields`);
  }

  getAll(tournamentId: number): Observable<Coach[]> {
    return this.http.get<Coach[]>(`${this.url(tournamentId)}/`);
  }

  getClubs(tournamentId: number): Observable<Club[]> {    
    return this.http.get<Club[]>(`${this.apiUrl}/${tournamentId}/clubs`);
  }

  create(tournamentId: number, data: Partial<Coach>): Observable<Coach> {
    return this.http.post<Coach>(`${this.url(tournamentId)}/`, data);
  }

  update(
    tournamentId: number,
    coachId: number,
    data: Partial<Coach>
  ): Observable<Coach> {
    return this.http.put<Coach>(
      `${this.url(tournamentId)}/${coachId}`,
      data
    );
  }

  delete(tournamentId: number, coachId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.url(tournamentId)}/${coachId}`
    );
  }

}