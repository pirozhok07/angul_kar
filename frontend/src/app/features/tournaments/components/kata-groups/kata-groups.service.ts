import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { Athlete } from '../athletes/athletes.service';
import { Category } from '../categories/categories.service';
import { Club } from '../clubs/clubs.service';


export interface KataGroup {
  id: number;
  [key: string]: unknown;
}

export interface KataGroupField {
  name: string;
  type: string;
  nullable: boolean;
  required: boolean;
}

export type KataGroupPayload = Record<string, unknown>;

@Injectable({
    providedIn: 'root'
})
export class KataGroupsService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments';

  private url(tournamentId: number): string {
    return `${this.apiUrl}/${tournamentId}/kata-groups`;
  }

  getFields(tournamentId: number): Observable<KataGroupField[]> {
    return this.http.get<KataGroupField[]>(`${this.url(tournamentId)}/fields`);
  }

  getAll(tournamentId: number): Observable<KataGroup[]> {
    return this.http.get<KataGroup[]>(`${this.url(tournamentId)}/`);
  }

  getAthletes(tournamentId: number): Observable<Athlete[]> {    
    return this.http.get<Athlete[]>(`${this.apiUrl}/${tournamentId}/athletes`);
  }

  getCategories(tournamentId: number): Observable<Category[]> {    
    return this.http.get<Category[]>(`${this.apiUrl}/${tournamentId}/categories`);
  }

  getClubs(tournamentId: number): Observable<Club[]> {    
    return this.http.get<Club[]>(`${this.apiUrl}/${tournamentId}/clubs`);
  }

  create(tournamentId: number, data: KataGroupPayload): Observable<KataGroup> {
    return this.http.post<KataGroup>(`${this.url(tournamentId)}/`, data);
  }

  update(
    tournamentId: number,
    kata_groupsId: number,
    data: KataGroupPayload
  ): Observable<KataGroup> {
    return this.http.put<KataGroup>(
      `${this.url(tournamentId)}/${kata_groupsId}`,
      data
    );
  }

  delete(tournamentId: number, kata_groupsId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.url(tournamentId)}/${kata_groupsId}`
    );
  }

}