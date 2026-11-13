import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import { form } from "@angular/forms/signals";
import { Club } from "../clubs/clubs.service";
import { Coach } from "../coaches/coaches.service";

export interface Athlete {
    id: number;
    [key: string]: unknown;
}

export interface AthleteField {
    name: string;
    type: string;
    nullable: boolean;
    required: boolean;
}

export interface ImportPreviewRow {
    row: number;
    full_name: string;
    data: Record<string, unknown>;
    errors: string[];
    valid: boolean;
}
export interface ImportPreview {
    total: number;
    valid: number;
    invalid: number;
    rows: ImportPreviewRow[];
}
export interface ImportResult {
    imported: number;
    message: string;
}

@Injectable({ 
    providedIn: 'root'
 })
export class AthletesService {
    
    private readonly http = inject(HttpClient);

    private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments';

    private url(tournamentId: number): string {
        return `${this.apiUrl}/${tournamentId}/athletes`;
    }

    getFields(tournamentId: number): Observable<AthleteField[]> {
        return this.http.get<AthleteField[]>(`${this.url(tournamentId)}/fields`);
    }

    getAll(tournamentId: number): Observable<Athlete[]> {
        return this.http.get<Athlete[]>(`${this.url(tournamentId)}/`);
    }

    getById(
        tournamentId: number,
        athleteId: number,
    ): Observable<Athlete> {
        return this.http.get<Athlete>(`${this.url(tournamentId)}/${athleteId}`);
    }

    getClubs(tournamentId: number): Observable<Club[]> {    
        return this.http.get<Club[]>(`${this.apiUrl}/${tournamentId}/clubs`);
    }
      
    getCoaches(tournamentId: number): Observable<Coach[]> {    
        return this.http.get<Coach[]>(`${this.apiUrl}/${tournamentId}/coaches`);
    }

    create(
        tournamentId: number,
        data: Record<string, unknown>
    ): Observable<Athlete> {
        return this.http.post<Athlete>(`${this.url(tournamentId)}/`, data);
    }

    update(
        tournamentId: number,
        athleteId: number,
        data: Record<string, unknown>
    ): Observable<Athlete> {
        return this.http.put<Athlete>(`${this.url(tournamentId)}/${athleteId}`, data);
    }

    delete(
        tournamentId: number,
        athleteId: number,
    ): Observable<Athlete> {
        return this.http.delete<Athlete>(`${this.url(tournamentId)}/${athleteId}`);
    }

    downloadTemplate(tournamentId: number) {
        return this.http.get(`${this.url(tournamentId)}/import/template`, { responseType: 'blob' });
    }

    previewImport(tournamentId: number, file: File) {
        const formData = new FormData();
        formData.append('file', file);

        return this.http.post<ImportPreview>(`${this.url(tournamentId)}/import/preview`, formData );
    }

    confirmImport(tournamentId: number, file: File) {
        const formData = new FormData();
        formData.append('file', file);

        return this.http.post<ImportResult>(`${this.url(tournamentId)}/import/confirm`, formData );
    }
}