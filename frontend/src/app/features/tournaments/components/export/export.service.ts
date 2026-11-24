import { Injectable, inject } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { Observable } from "rxjs";
import { form } from "@angular/forms/signals";
import { Club } from "../clubs/clubs.service";
import { Coach } from "../coaches/coaches.service";


@Injectable({ 
    providedIn: 'root'
 })
export class ExportService {
    
    private readonly http = inject(HttpClient);

    private readonly apiUrl = 'http://127.0.0.1:8000/api/tournaments';

    private url(tournamentId: number): string {
        return `${this.apiUrl}/${tournamentId}/export`;
    }

    categories(tournamentId: number) {
        return this.http.get(`${this.url(tournamentId)}/categories`, {responseType: 'blob'});
    }

    kata(tournamentId: number) {
        return this.http.get(`${this.url(tournamentId)}/kata`, {responseType: 'blob'});
    }

    kumite(tournamentId: number) {
        return this.http.get(`${this.url(tournamentId)}/kumite`, {responseType: 'blob'});
    }

    results(tournamentId: number) {
        return this.http.get(`${this.url(tournamentId)}/results`, {responseType: 'blob'});
    }

}