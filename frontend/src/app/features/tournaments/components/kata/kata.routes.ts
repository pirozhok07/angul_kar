import { Routes } from '@angular/router';

import { KataDraw }  from './kata-draw/kata-draw';

export const KATA_DRAWS_ROUTES: Routes = [
    {
        path: '',
        component: KataDraw
    },
];
