import { TestBed } from '@angular/core/testing';
import { Athletes } from './athletes';

describe('Athletes', () => {
  let service: Athletes;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Athletes);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
