import { Routes } from '@angular/router';

import { AthletesList }  from './athletes-list/athletes-list';
import { AthletesImport }  from './athletes-import/athletes-import';

export const ATHLETES_ROUTES: Routes = [
    {
        path: '',
        component: AthletesList
    },
    {
        path: 'import',
        component: AthletesImport
    }
];
