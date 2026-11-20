import { Routes } from '@angular/router';

import { TournamentMain } from './features/tournaments/components/tournaments/tournament-main/tournament-main';
import { TournamentDashboard } from './features/tournaments/components/tournaments/tournament-dashboard/tournament-dashboard';
import { ATHLETES_ROUTES } from './features/tournaments/components/athletes/athletes.routes';
import { CATEGORIES_ROUTES } from './features/tournaments/components/categories/categories.routes';
import { CLUBS_ROUTES } from './features/tournaments/components/clubs/clubs.routes';
import { COACHES_ROUTES } from './features/tournaments/components/coaches/coaches.routes';
import { KATA_GROUPS_ROUTES } from './features/tournaments/components/kata-groups/kata-groups.routes';
import { COMPETITIONS_ROUTES } from './features/tournaments/components/competition/competitions.routes';

export const routes: Routes = [
    {
        path: '',
        pathMatch: 'full',
        redirectTo: "tournaments"
    },

    {
        path: 'tournaments',
        component: TournamentMain
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
            },
            {
                path: 'kata-groups',
                children: KATA_GROUPS_ROUTES
            },
            {
                path: 'competition',
                children: COMPETITIONS_ROUTES
            },
        ]
    },
    
    {
        path: '**',
        redirectTo: "tournaments"
    }
];
