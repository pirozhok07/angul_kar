import { Routes } from '@angular/router';

import { CoachesList }  from './coaches-list/coaches-list';

export const COACHES_ROUTES: Routes = [
    {
        path: '',
        component: CoachesList
    }
];
