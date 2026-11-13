import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';


export interface Club {
  id: number;
  [key: string]: unknown;
}

export interface ClubsField {
  name: string;
  type: string;
  nullable: boolean;
  required: boolean;
}

@Injectable({
    providedIn: 'root'
})
export class ClubsService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments';

  private url(tournamentId: number): string {
    return `${this.apiUrl}/${tournamentId}/clubs`;
  }

  getFields(tournamentId: number): Observable<ClubsField[]> {
    return this.http.get<ClubsField[]>(`${this.url(tournamentId)}/fields`);
  }

  getAll(tournamentId: number): Observable<Club[]> {
    return this.http.get<Club[]>(`${this.url(tournamentId)}/`);
  }

  create(tournamentId: number, data: Partial<Club>): Observable<Club> {
    return this.http.post<Club>(`${this.url(tournamentId)}/`, data);
  }

  update(
    tournamentId: number,
    clubId: number,
    data: Partial<Club>
  ): Observable<Club> {
    return this.http.put<Club>(
      `${this.url(tournamentId)}/${clubId}`,
      data
    );
  }

  delete(tournamentId: number, clubId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.url(tournamentId)}/${clubId}`
    );
  }

}