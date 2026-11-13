import { Routes } from '@angular/router';

import { TournamentList } from './features/tournaments/components/tournament-list/tournament-list';
import { TournamentDashboard } from './features/tournaments/components/tournament-dashboard/tournament-dashboard';
import { ATHLETES_ROUTES } from './features/tournaments/components/athletes/athletes.routes';
import { CATEGORIES_ROUTES } from './features/tournaments/components/categories/categories.routes';
import { CLUBS_ROUTES } from './features/tournaments/components/clubs/clubs.routes';
import { COACHES_ROUTES } from './features/tournaments/components/coaches/coaches.routes';

export const routes: Routes = [
    {
        path: '',
        pathMatch: 'full',
        redirectTo: "tournaments"
    },

    {
        path: 'tournaments',
        component: TournamentList
    },
    
    {
        path: 'tournaments/:id',
        component: TournamentDashboard,
        children: [
            {
                path: 'athletes',
                children: ATHLETES_ROUTES
            },
            {
                path: 'categories',
                children: CATEGORIES_ROUTES
            },
            {
                path: 'clubs',
                children: CLUBS_ROUTES
            },
            {
                path: 'coaches',
                children: COACHES_ROUTES
            }
        ]
    },
    
    {
        path: '**',
        redirectTo: "tournaments"
    }
];
