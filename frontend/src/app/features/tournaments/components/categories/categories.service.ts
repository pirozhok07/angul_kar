import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';


export interface Category {
  id: number;
  [key: string]: unknown;
}

export interface CategoryField {
  name: string;
  type: string;
  nullable: boolean;
  required: boolean;
}

@Injectable({
    providedIn: 'root'
})
export class CategoriesService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments';

  private url(tournamentId: number): string {
    return `${this.apiUrl}/${tournamentId}/categories`;
  }

  getFields(tournamentId: number): Observable<CategoryField[]> {
    return this.http.get<CategoryField[]>(`${this.url(tournamentId)}/fields`);
  }

  getAll(tournamentId: number): Observable<Category[]> {
    return this.http.get<Category[]>(`${this.url(tournamentId)}/`);
  }

  create(tournamentId: number, data: Partial<Category>): Observable<Category> {
    return this.http.post<Category>(`${this.url(tournamentId)}/`, data);
  }

  update(
    tournamentId: number,
    categoryId: number,
    data: Partial<Category>
  ): Observable<Category> {
    return this.http.put<Category>(
      `${this.url(tournamentId)}/${categoryId}`,
      data
    );
  }

  delete(tournamentId: number, categoryId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.url(tournamentId)}/${categoryId}`
    );
  }

  preview(tournamentId: number): Observable<any> {    
    return this.http.get<any>(
      `${this.url(tournamentId)}/distribution-preview`
    );
  }

  assign(tournamentId: number, assignments: {
    athlete_tournamentId: number;
    category_tournamentId: number;
  }[]): Observable<{ created: number }> {
    return this.http.post<{ created: number }>(
      `${this.url(tournamentId)}/assign`,
      assignments
    );
  }
}