import { Routes } from '@angular/router';

import { KumiteDraw }  from './kumite-draw/kumite-draw';

export const KUMITE_GROUPS_ROUTES: Routes = [
    {
        path: '',
        component: KumiteDraw
    }
];
