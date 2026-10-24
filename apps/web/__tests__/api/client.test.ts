import { ApiError, getListings, createRFQ } from '../../lib/api/client';

describe('STRATA API Client Tests', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    jest.resetAllMocks();
  });

  afterAll(() => {
    global.fetch = originalFetch;
  });

  it('1. Returns parsed data on 200 response', async () => {
    const mockData = {
      items: [
        {
          listing_id: 'listing-123',
          lot_id: 'lot-123',
          status: 'active',
          quantity: 50,
          unit: 'MT',
          material_type: 'Recycled Polyethylene',
          provenance_label: 'synthetic_demo',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: jest.fn().mockResolvedValue(mockData),
    } as any);

    const result = await getListings({ view: 'all' });
    expect(result).toEqual(mockData);
    expect(result.items.length).toBe(1);
    expect(result.items[0].material_type).toBe('Recycled Polyethylene');
  });

  it('2. Throws typed ApiError on 401 response with correct status and message', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: jest.fn().mockResolvedValue({ detail: 'Invalid authentication credentials' }),
    } as any);

    await expect(getListings()).rejects.toThrow(ApiError);

    try {
      await getListings();
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(401);
      expect(err.message).toBe('Invalid authentication credentials');
      expect(err.endpoint).toBe('/marketplace/listings');
    }
  });

  it('3. Throws typed ApiError on 500 response', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: jest.fn().mockResolvedValue({ detail: 'Database connection failed' }),
    } as any);

    await expect(
      createRFQ({
        listing_id: 'listing-fail',
        requested_quantity: 10,
      })
    ).rejects.toThrow(ApiError);

    try {
      await createRFQ({
        listing_id: 'listing-fail',
        requested_quantity: 10,
      });
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(500);
      expect(err.message).toBe('Database connection failed');
    }
  });

  it('4. Adds Authorization header when token is provided', async () => {
    const mockResponse = { data: { rfq_id: 'rfq-777', status: 'draft' } };
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: jest.fn().mockResolvedValue(mockResponse),
    } as any);
    global.fetch = mockFetch;

    await createRFQ(
      {
        listing_id: 'listing-999',
        requested_quantity: 25,
      },
      'bearer-jwt-token-123',
      'org-surat-textiles'
    );

    expect(mockFetch).toHaveBeenCalled();
    const calledOptions = mockFetch.mock.calls[0][1];
    expect(calledOptions.headers['Authorization']).toBe('Bearer bearer-jwt-token-123');
    expect(calledOptions.headers['X-Org-Id']).toBe('org-surat-textiles');
  });

  it('5. Raises clear error if NEXT_PUBLIC_API_URL is missing at import time', () => {
    const originalEnv = process.env.NEXT_PUBLIC_API_URL;
    delete process.env.NEXT_PUBLIC_API_URL;

    expect(() => {
      jest.isolateModules(() => {
        require('../../lib/api/client');
      });
    }).toThrow('NEXT_PUBLIC_API_URL is not set. Check .env.local.');

    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  });
});
