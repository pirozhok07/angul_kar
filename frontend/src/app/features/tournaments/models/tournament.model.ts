export interface Tournament {
    id: number;
    name: string;
    location: string;
    start_date: string;
    end_date: string;
    description: string | null;
    database_status: string;
}

export interface TournamentCreate {
    name: string;
    location: string;
    start_date: string;
    end_date: string;
    description: string | null;
}