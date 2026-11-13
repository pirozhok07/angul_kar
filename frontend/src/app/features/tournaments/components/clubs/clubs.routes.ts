import { Routes } from '@angular/router';

import { ClubsList }  from './clubs-list/clubs-list';

export const CLUBS_ROUTES: Routes = [
    {
        path: '',
        component: ClubsList
    }
];
